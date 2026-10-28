#!/usr/bin/env python3
"""Board status switchers: cheap, no agy run. One mode per systemd timer.

  board_switch.py unblock   blocked -> todo   (prerequisite task merged, or bounded auto-retry)
  board_switch.py review    review  -> done | todo | blocked   (decided by the task's PR + local CI);
                            primes CI for EVERY agy task with an open PR and no CI verdict yet,
                            regardless of board status (not just 'review') -- a task sitting in
                            todo/blocked/in-progress with a real PR must not leave that PR's CI silent
  board_switch.py audit     consistency + bridge-health audit (see board_audit.py) -- flags only,
                            never changes task status except where board_audit.py says so explicitly
  board_switch.py sprint    sprint lifecycle (see sprint-manager.py `auto`) -- closes+archives any
                            sprint-NN that is ALL DONE and activates sprint-NN+1 (planning -> active).
                            Generic: works for whichever sprint number is currently done, no number
                            hardcoded. Only flips folders/flags; never invents tasks.

The executor (board_agy_bridge.py) only runs `todo` tasks; it parks a finished task in `review`
while its PR is open. Verdicts come from GitHub (PR state) and ~/Apps/dev-ci commit statuses,
so nothing is mirrored into the task JSON except `status` and a note.
"""
import datetime
import importlib.util
import json
import re
import subprocess
import sys

import board_agy_bridge as B
import board_audit as A

_SPRINT_MGR_PATH = B.BOARD / "sprint-manager.py"
_spec = importlib.util.spec_from_file_location("sprint_manager", _SPRINT_MGR_PATH)
sprint_manager = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sprint_manager)

MAX_AUTO_RETRY = 3                  # blocked-without-prereq tasks: auto-retries
RETRY_BACKOFF_MIN = [10, 30, 90]    # wait before each retry
MAX_CI_FIX = 3                      # agy fix attempts per PR before a human is needed
MAX_CI_ERROR_RETRY = 3              # CI infra-error restarts per PR head before leaving it to a human
ERROR_RETRY_MIN = 10                # same wait ci-poller applies before re-running an `error` head


def _age_min(iso):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(iso)).total_seconds() / 60


def _note(t, msg):
    t["notes"] = ((t.get("notes") or "") + f" | {msg} {B._now()[:16]}").strip(" |")


def _set(f, t, status, msg, event):
    t["status"] = status
    t["updated"] = B._now()
    _note(t, msg)
    B._save(f, t)
    B._log_event(event, t.get("id", ""), t.get("title", ""), detail=msg)
    print(f"{t.get('id')} -> {status}: {msg}")


def _prereq_task(task):
    m = re.search(r"PRASYARAT.*?(TASK-\d+)", task.get("description", "") or "")
    return m.group(1) if m else ""


def _has_sprint_prereq(task):
    """Detect if task is gated on an entire sprint completion."""
    return bool(re.search(r"PRASYARAT.*?(Sprint\s+\d+|sprint-\d+)", task.get("description", "") or "", re.IGNORECASE))


def _sprint_prereq_num(task):
    """Highest sprint number a task's description names as its prerequisite.
    Handles both a single sprint ('Menunggu Sprint 04 selesai') and a range
    ('Menunggu ... Sprint 04 s.d. Sprint 07' / 's/d Sprint 07') by taking the
    MAX number mentioned in the prerequisite clause — the range's tail is the
    actual gate, since sprints close in order. Generic — any number."""
    desc = task.get("description", "") or ""
    m = re.search(r"PRASYARAT[^.]*\.", desc, re.IGNORECASE) or re.search(r"Blocked:[^|]*", desc, re.IGNORECASE)
    scope = m.group(0) if m else desc
    nums = []
    for a, b in re.findall(r"Sprint\s+0*(\d+)|sprint-0*(\d+)", scope, re.IGNORECASE):
        nums.append(int(a or b))
    return max(nums) if nums else None


def _sprint_closed(nn):
    """Is sprint-NN finished (archived, or its own SPRINT.md says closed/done)?
    Checking archive/ first covers the normal case (sprint-manager.py close()
    moves the whole folder there); the SPRINT.md status is a fallback for a
    sprint that was marked done without being moved yet."""
    if (B.BOARD / "archive" / f"sprint-{nn:02d}").is_dir():
        return True
    sp = B.BOARD / "sprints" / f"sprint-{nn:02d}" / "SPRINT.md"
    if sp.is_file():
        txt = sp.read_text(encoding="utf-8")
        if re.search(r"^status:\s*(closed|done)\s*$", txt, re.M):
            return True
    return False


def _branch_pr_merged(branch):
    if not branch:
        return False
    try:
        r = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "merged",
                            "--json", "number", "--limit", "1"],
                           cwd=str(B.GALLEON), capture_output=True, text=True, timeout=60)
        return bool(json.loads(r.stdout or "[]"))
    except Exception:
        return False


def _trigger_agy_bridge():
    """Trigger agy bridge service immediately via systemd without blocking."""
    try:
        subprocess.run(["systemctl", "--user", "start", "--no-block", "agy-bridge.service"],
                       capture_output=True, timeout=5)
    except Exception:
        pass


def unblock():
    files = {}
    for f in B._active_task_files():
        t = B._load(f)
        if t:
            files[t.get("id")] = (f, t)
    unblocked_count = 0
    for tid, (f, t) in files.items():
        if t.get("assignee") != "agy" or t.get("status") != "blocked":
            continue
        if _has_sprint_prereq(t):
            # Gated on a previous sprint completion — NOT an orphan failure, do not auto-retry.
            # But DO advance it once that sprint is actually closed (sequencing gate satisfied).
            nn = _sprint_prereq_num(t)
            if nn is not None and _sprint_closed(nn):
                _set(f, t, "todo", f"auto-unblock: sprint-{nn:02d} selesai & diarsipkan", "unblock")
                unblocked_count += 1
            continue
        prereq = _prereq_task(t)
        if not prereq or prereq not in files:
            # blocked WITHOUT a prerequisite = an agy failure, not a sequencing gate.
            n, last = B._retry_state(tid)
            if n >= MAX_AUTO_RETRY:
                continue  # exhausted: needs the manual retry button
            if last:
                try:
                    elapsed = (datetime.datetime.now(datetime.timezone.utc)
                               - datetime.datetime.fromisoformat(last)).total_seconds() / 60
                except Exception:
                    elapsed = 1e9
                if elapsed < RETRY_BACKOFF_MIN[min(n, len(RETRY_BACKOFF_MIN) - 1)]:
                    continue
            B._retry_bump(tid, "auto-retry (blocked tanpa prereq)")
            _set(f, t, "todo", f"auto-retry {n + 1}/{MAX_AUTO_RETRY}", "retry")
            unblocked_count += 1
            continue
        _, pt = files[prereq]
        # the prerequisite's PR must be merged (same crate = avoid conflicts)
        if pt.get("status") in ("done", "review") and _branch_pr_merged(B._expected_branch(pt)):
            _set(f, t, "todo", f"auto-unblock: {prereq} done+merged", "unblock")
            unblocked_count += 1
    if unblocked_count > 0:
        _trigger_agy_bridge()
    return unblocked_count


def _prime_ci():
    """CI trigger must not be gated on task status ('review' only): a task can sit in
    `todo`/`blocked`/`in-progress` on the board (its own executor hasn't caught up yet,
    or a human pushed a fix commit directly to its branch — as happened manually here)
    while its PR already has a real head commit with no CI verdict at all. Without this,
    that PR's CI stays silent until the task's own status happens to become `review`,
    which can be hours away or may never happen if nothing re-dispatches the task.
    Scan every agy task with an existing PR (any board status) and start CI for any
    head SHA that has no verdict yet (state is None) or errored — identical gate to
    review()'s own trigger, just not restricted to status == 'review'. `_trigger_ci`
    itself is idempotent (duplicate unit name is rejected), so this is safe to run
    alongside review()'s own trigger for 'review' tasks without double-starting CI."""
    for f in B._active_task_files():
        t = B._load(f)
        if not t or t.get("assignee") != "agy" or t.get("status") in ("review", "done"):
            continue  # 'review' tasks are primed by review() below; 'done' has nothing left to verify
        branch = B._expected_branch(t)
        pr = B._branch_pr(branch)
        if not pr or pr["state"] != "OPEN":
            continue
        state, _, _ = B._ci_state(pr)
        if state in (None, "error"):
            B._trigger_ci(pr["number"], pr["headRefOid"])


def review():
    _prime_ci()
    done_count = 0
    for f in B._active_task_files():
        t = B._load(f)
        if not t or t.get("assignee") != "agy" or t.get("status") != "review":
            continue
        branch = B._expected_branch(t)
        pr = B._branch_pr(branch)
        if not pr:
            continue
        n = pr["number"]
        if pr["state"] == "MERGED":
            _set(f, t, "done", f"PR #{n} merged", "done")
            B._cleanup_stale_ci_poller(n)  # fix #3: review() closed it independently of
                                            # board_agy_bridge.py's own run() — any ci-poller
                                            # for this PR still polling has no more work.
            done_count += 1
        elif pr["state"] == "CLOSED":
            _set(f, t, "blocked", f"PR #{n} ditutup tanpa merge", "blocked")
        else:
            state, red, _ = B._ci_state(pr)
            if state in (None, "pending", "error"):
                # No final verdict for this head: start CI (a duplicate start for the same head is rejected).
                if state == "error":   # infra error: retry with backoff, then leave it to a human
                    ekey = f"ci-err-{n}-{pr['headRefOid'][:8]}"
                    etries, elast = B._retry_state(ekey)
                    if etries >= MAX_CI_ERROR_RETRY or (elast and _age_min(elast) < ERROR_RETRY_MIN):
                        continue
                    B._retry_bump(ekey, "ci error")
                B._trigger_ci(n, pr["headRefOid"])
                continue
            if state != "failure":
                # Green/success: jika PR sudah lolos CI tapi belum dimerge (mis. poller exit sebelum
                # GitHub status siap), coba squash-merge otomatis agar review tidak wedge/tergantung.
                if state == "success" and pr.get("baseRefName") == "testing" and branch.startswith("feat/"):
                    sha = pr.get("headRefOid", "")
                    try:
                        v_cmd = ["gh", "pr", "view", str(n), "-R", "diezy-realm/galleon-fleet",
                                 "--json", "mergeable,reviewDecision,headRefOid"]
                        v_res = subprocess.run(v_cmd, cwd=str(B.GALLEON), capture_output=True, text=True, timeout=30)
                        if v_res.returncode == 0:
                            v = json.loads(v_res.stdout)
                            if (v.get("mergeable") == "MERGEABLE"
                                    and v.get("reviewDecision") != "CHANGES_REQUESTED"
                                    and v.get("headRefOid") == sha):
                                m_cmd = ["gh", "pr", "merge", str(n), "-R", "diezy-realm/galleon-fleet",
                                         "--squash", "--match-head-commit", sha]
                                m_res = subprocess.run(m_cmd, cwd=str(B.GALLEON), capture_output=True, text=True, timeout=60)
                                if m_res.returncode == 0:
                                    _set(f, t, "done", f"PR #{n} merged (auto-merge)", "done")
                                    B._cleanup_stale_ci_poller(n)  # fix #3
                                    done_count += 1
                                    continue
                    except Exception:
                        pass
                continue  # green: merge sedang diproses atau menunggu giliran
            key = f"ci-pr-{n}"
            tries, _ = B._retry_state(key)
            if tries >= MAX_CI_FIX:
                _set(f, t, "blocked", f"CI merah setelah {tries} perbaikan agy pada PR #{n}: {', '.join(red)}", "blocked")
            else:
                B._retry_bump(key, f"ci red: {','.join(red)}")
                _set(f, t, "todo", f"CI merah PR #{n} ({', '.join(red)}), perbaikan {tries + 1}/{MAX_CI_FIX}", "ci-fix")
                _trigger_agy_bridge()
    if done_count > 0:
        unblock()


MODES = {"unblock": unblock, "review": review, "audit": A.run, "sprint": sprint_manager.auto}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        sys.exit(__doc__)
    MODES[sys.argv[1]]()
