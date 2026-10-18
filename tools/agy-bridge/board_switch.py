#!/usr/bin/env python3
"""Board status switchers: cheap, no agy run. One mode per systemd timer.

  board_switch.py unblock   blocked -> todo   (prerequisite task merged, or bounded auto-retry)
  board_switch.py review    review  -> done | todo | blocked   (decided by the task's PR + local CI)

The executor (board_agy_bridge.py) only runs `todo` tasks; it parks a finished task in `review`
while its PR is open. Verdicts come from GitHub (PR state) and ~/Apps/dev-ci commit statuses,
so nothing is mirrored into the task JSON except `status` and a note.
"""
import datetime
import json
import re
import subprocess
import sys

import board_agy_bridge as B

MAX_AUTO_RETRY = 3                  # blocked-without-prereq tasks: auto-retries
RETRY_BACKOFF_MIN = [10, 30, 90]    # wait before each retry
MAX_CI_FIX = 3                      # agy fix attempts per PR before a human is needed


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
    m = re.search(r"PRASYARAT:\s*(TASK-\d+)", task.get("description", "") or "")
    return m.group(1) if m else ""


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


def unblock():
    files = {}
    for f in B._active_task_files():
        t = B._load(f)
        if t:
            files[t.get("id")] = (f, t)
    for tid, (f, t) in files.items():
        if t.get("assignee") != "agy" or t.get("status") != "blocked":
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
            continue
        _, pt = files[prereq]
        # the prerequisite's PR must be merged (same crate = avoid conflicts)
        if pt.get("status") in ("done", "review") and _branch_pr_merged(B._expected_branch(pt)):
            _set(f, t, "todo", f"auto-unblock: {prereq} done+merged", "unblock")


def review():
    for f in B._active_task_files():
        t = B._load(f)
        if not t or t.get("assignee") != "agy" or t.get("status") != "review":
            continue
        pr = B._branch_pr(B._expected_branch(t))
        if not pr:
            continue
        n = pr["number"]
        if pr["state"] == "MERGED":
            _set(f, t, "done", f"PR #{n} merged", "done")
        elif pr["state"] == "CLOSED":
            _set(f, t, "blocked", f"PR #{n} ditutup tanpa merge", "blocked")
        else:
            state, red, _ = B._ci_state(pr)
            if state != "failure":
                continue  # green (poller merges), pending, or not reported yet
            key = f"ci-pr-{n}"
            tries, _ = B._retry_state(key)
            if tries >= MAX_CI_FIX:
                _set(f, t, "blocked", f"CI merah setelah {tries} perbaikan agy pada PR #{n}: {', '.join(red)}", "blocked")
            else:
                B._retry_bump(key, f"ci red: {','.join(red)}")
                _set(f, t, "todo", f"CI merah PR #{n} ({', '.join(red)}), perbaikan {tries + 1}/{MAX_CI_FIX}", "ci-fix")


MODES = {"unblock": unblock, "review": review}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        sys.exit(__doc__)
    MODES[sys.argv[1]]()
