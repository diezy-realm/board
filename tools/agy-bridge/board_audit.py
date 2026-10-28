"""Board audit: cheap, no agy run. One more mode for the same systemd timer as board_switch.py.

  board_audit.py run

Scope -- what this checks and what it does about it (deterministic, no LLM):

1. STALE task (claim yatim): `in-progress`/`review` with no live agy process AND
   no fresh commit on its expected branch for STALE_MIN minutes -> flag in notes,
   do NOT touch status. A human (or KiroCrew) decides the reset, same as the
   TASK-016/017 incidents this audit exists to catch early.

2. PARENT/EPIC vs sub-tasks: if an EPIC's own sub-tasks are all "done" but the EPIC
   itself is not, or an EPIC is "done" while a sub-task has regressed, FLAG it in
   notes for a human/KiroCrew to confirm (never auto-closes — closing an EPIC can
   require extra verification beyond "children done", as the TASK-001 incident
   proved: a literal grep count, not just sub-task status).

3. STALE notes: a task's `notes` mentions "PR #<N>" — if that PR's real state
   (gh pr view) no longer matches what the note implies (OPEN vs MERGED/CLOSED),
   flag it so the note gets corrected instead of staying stale forever.

4. BRIDGE health: if no bridge event (processed/blocked, see `_log_event` in
   board_agy_bridge.py) has landed in HEALTH_MAX_MIN minutes *while* at least
   one agy task is todo/in-progress, agy/bridge itself may be stuck -> notify.
   A quiet board (nothing agy-assigned pending) is NOT a health problem.

5. RED CI at review: a task in `review` whose OPEN PR has a FAILING required CI
   gate (local/Required Gate) for more than STALE_MIN minutes -> flag. This is
   NOT "work in progress" and was previously invisible: check_stale_claims()
   only looks at commit recency, check_stale_notes() only looks at PR
   open/merged/closed state — neither notices a PR that is open AND red.

Writes only: task `notes` (append, never overwrites), task `status` for rule 2
only, and a notification via ctx.notify() when invoked as a cron. Running this
file directly (`python3 board_audit.py run`) prints findings to stdout.
"""
import datetime
import json
import re
import subprocess
import sys

import board_agy_bridge as B

STALE_MIN = 60          # in-progress/review with no sign of life -> flag (claim yatim)
HEALTH_MAX_MIN = 60     # no bridge event at all while work is pending -> flag bridge health
_EPIC_SUBTASK_RE = re.compile(r"\bTASK-\d+\b")
# Only a task explicitly titled "EPIC" AND whose own acceptance criteria literally
# say "sub-task ... done & PR merged" counts — avoids misfiring on a normal task
# that merely MENTIONS other TASK-XXX ids for context (e.g. "gap TASK-004").
_EPIC_TITLE_RE = re.compile(r"\bEPIC\b", re.IGNORECASE)
_EPIC_ACCEPTANCE_RE = re.compile(r"sub-task.*done.*merged", re.IGNORECASE)


def _age_min(iso):
    try:
        return (datetime.datetime.now(datetime.timezone.utc)
                - datetime.datetime.fromisoformat(iso)).total_seconds() / 60
    except Exception:
        return 1e9


def _flag(f, t, msg):
    """Append an audit flag to notes WITHOUT touching status — a human/KiroCrew decides."""
    existing = t.get("notes") or ""
    tag = f"AUDIT {B._now()[:16]}: {msg}"
    if tag[:40] in existing:   # avoid re-flagging the same finding every cycle
        return False
    t["notes"] = (existing + f" | {tag}").strip(" |")
    t["updated"] = B._now()
    B._save(f, t)
    B._log_event("audit", t.get("id", ""), t.get("title", ""), detail=msg)
    return True


def _agy_alive():
    """True if ANY `agy` process is running on the host. BUG HISTORY: this used to be
    the sole liveness gate in check_stale_claims(), which made it a proxy for ALL
    tasks at once — one agy process (working on task A) silently exempted every OTHER
    in-progress/review task from ever being flagged, even one genuinely abandoned.
    Kept as a cheap first filter only; check_stale_claims() now also requires the
    specific task's OWN branch to show recent commit activity before skipping a flag."""
    try:
        r = subprocess.run(["pgrep", "-x", "agy"], capture_output=True, text=True, timeout=5)
        return bool(r.stdout.strip())
    except Exception:
        return False


def _branch_has_recent_commit(branch, within_min):
    """True if `branch` has a commit newer than within_min ago (local or origin)."""
    if not branch:
        return False
    for ref in (branch, f"origin/{branch}"):
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%cI", ref],
                               cwd=str(B.GALLEON), capture_output=True, text=True, timeout=20)
            ts = (r.stdout or "").strip()
            if ts and _age_min(ts) < within_min:
                return True
        except Exception:
            continue
    return False


def check_stale_claims():
    """Rule 1: in-progress/review task, no sign of life ON THIS TASK'S OWN BRANCH,
    no recent commit -> flag (never auto-reset).

    A live `agy` process is only a per-task alibi when that task's own expected
    branch ALSO shows a recent commit — a lone global `_agy_alive()` would let one
    process working on task A silently exempt every other in-progress/review task
    from ever being flagged (verified bug: this previously skipped the whole check
    whenever any agy process existed anywhere, regardless of which task it served)."""
    flagged = []
    agy_up = _agy_alive()
    for f, t in _all_tasks().values():
        if t.get("assignee") != "agy" or t.get("status") not in ("in-progress", "review"):
            continue
        if _age_min(t.get("updated", t.get("created", B._now()))) < STALE_MIN:
            continue
        branch = B._expected_branch(t)
        has_recent_commit = _branch_has_recent_commit(branch, STALE_MIN)
        if has_recent_commit:
            continue  # this task's own branch moved recently — genuinely active
        if agy_up and _age_min(t.get("updated", "")) < STALE_MIN * 2:
            # a process exists AND this task was touched less than 2x the stale
            # window ago — plausibly the one agy is working on right now (no
            # per-task PID available), give it one more cycle before flagging.
            continue
        msg = (f"status '{t['status']}' sejak >{STALE_MIN}min, tidak ada commit baru di "
               f"branch '{branch or '?'}' milik task ini (agy proses lain mungkin hidup, "
               "tapi itu bukan bukti task INI yang dikerjakan) -- kemungkinan claim yatim. "
               "Cek manual (ps aux + git log + agy_conversation_id) sebelum reset.")
        if _flag(f, t, msg):
            flagged.append(t["id"])
    return flagged


def check_red_ci_review():
    """Rule 5: task in 'review' with an OPEN PR whose required CI gate is failing,
    and the failure is not fresh (gave agy/human time to react) -> flag. Without
    this, a PR can sit red indefinitely in 'review' and nothing ever says so —
    check_stale_claims() only tracks commit recency, not CI outcome, and
    check_stale_notes() only tracks PR open/merged/closed state, not checks."""
    flagged = []
    for f, t in _all_tasks().values():
        if t.get("status") != "review":
            continue
        branch = B._expected_branch(t)
        pr = B._branch_pr(branch)
        if not pr or pr.get("state") != "OPEN":
            continue
        state, red, _logdir = B._ci_state(pr)
        if state != "failure":
            continue
        if _age_min(t.get("updated", t.get("created", B._now()))) < STALE_MIN:
            continue  # give it one cycle to self-heal via re-dispatch before flagging
        gates = ", ".join(red) or "?"
        msg = (f"PR #{pr['number']} ({branch}) status 'review' tapi CI gate wajib MERAH "
               f"sejak >{STALE_MIN}min (gagal: {gates}) -- bukan 'sedang proses', task "
               "ini butuh fix sebelum bisa lanjut. Cek log dev-ci/logs/galleon-fleet.")
        if _flag(f, t, msg):
            flagged.append(f"{t['id']} (PR #{pr['number']})")
    return flagged


def _all_tasks():
    out = {}
    for f in B._active_task_files():
        t = B._load(f)
        if t:
            out[t.get("id", f.stem)] = (f, t)
    return out


def check_parent_sync():
    """Rule 2: EPIC status vs its sub-tasks. FLAG ONLY — never auto-apply. The TASK-001
    incident proved "all children done" is NOT sufficient to close an EPIC (its own DoD
    can require extra verification, e.g. a literal grep count); a human/KiroCrew must
    confirm before closing or reopening. Only a task that is unambiguously an EPIC
    (title says EPIC AND acceptance literally lists "sub-task ... done ... merged")
    is considered, so a normal task that merely mentions other TASK-XXX ids for
    context is never misidentified as one."""
    tasks = _all_tasks()
    flagged = []
    for tid, (f, t) in tasks.items():
        title = t.get("title", "") or ""
        acc_blob = " ".join(t.get("acceptance") or [])
        if not (_EPIC_TITLE_RE.search(title) and _EPIC_ACCEPTANCE_RE.search(acc_blob)):
            continue
        children = sorted(set(_EPIC_SUBTASK_RE.findall(acc_blob)) - {tid})
        if len(children) < 2:
            continue
        child_statuses = {c: tasks[c][1].get("status") for c in children if c in tasks}
        if len(child_statuses) < len(children):
            continue  # some child not found (archived?) — don't guess
        all_done = all(s == "done" for s in child_statuses.values())
        if all_done and t.get("status") != "done":
            msg = (f"semua sub-task ({', '.join(children)}) status done, tapi EPIC masih "
                   f"'{t['status']}' -- cek DoD tambahan (mis. grep literal) sebelum menutup.")
            if _flag(f, t, msg):
                flagged.append(f"{tid} (siap ditutup, perlu verifikasi DoD)")
        elif not all_done and t.get("status") == "done":
            regressed = [c for c, s in child_statuses.items() if s != "done"]
            msg = f"EPIC sudah 'done' tapi sub-task regresi dari done: {', '.join(regressed)}."
            if _flag(f, t, msg):
                flagged.append(f"{tid} (regresi, perlu dibuka ulang)")
    return flagged


def check_stale_notes():
    """Rule 3: notes mention 'PR #<N>' with an implied state (OPEN/MERGED/CLOSED) that no
    longer matches gh's real state for that PR -> flag so the note gets corrected."""
    flagged = []
    for f, t in _all_tasks().values():
        notes = t.get("notes") or ""
        m = re.search(r"PR\s*#(\d+)[^)]*?\((OPEN|MERGED|CLOSED)\)|PR\s*#(\d+)\s+(masih\s+OPEN|MERGED|ditutup)",
                      notes, re.IGNORECASE)
        if not m:
            continue
        num = m.group(1) or m.group(3)
        implied = (m.group(2) or m.group(4) or "").upper()
        implied = "OPEN" if "OPEN" in implied else ("MERGED" if "MERGED" in implied else "CLOSED")
        try:
            r = subprocess.run(["gh", "pr", "view", num, "--json", "state"],
                               cwd=str(B.GALLEON), capture_output=True, text=True, timeout=20)
            real = json.loads(r.stdout or "{}").get("state", "")
        except Exception:
            continue
        if real and real != implied:
            msg = f"notes sebut PR #{num} ({implied}) tapi state nyata sekarang {real} -- notes basi."
            if _flag(f, t, msg):
                flagged.append(t["id"])
    return flagged


def check_bridge_health(ctx=None):
    """Rule 4: agy work is pending (todo/in-progress) but no bridge event landed in
    HEALTH_MAX_MIN minutes -> bridge/agy itself may be stuck. Quiet board = no alert."""
    pending = [t for _, t in _all_tasks().values()
               if t.get("assignee") == "agy" and t.get("status") in ("todo", "in-progress")]
    if not pending:
        return None  # nothing for agy to do — silence is correct, not a health problem
    try:
        c = B._db()
        row = c.execute("SELECT ts FROM events ORDER BY ts DESC LIMIT 1").fetchone()
        c.close()
        last_ts = row[0] if row else None
    except Exception:
        last_ts = None
    age = _age_min(last_ts) if last_ts else 1e9
    if age < HEALTH_MAX_MIN:
        return None
    ids = ", ".join(t["id"] for t in pending[:5])
    msg = (f"⚠ Bridge health: {len(pending)} task agy pending ({ids}) tapi TIDAK ADA event "
           f"bridge baru selama {int(age)} menit (ambang {HEALTH_MAX_MIN}min). "
           "Cek: systemctl --user status agy-bridge.timer agy-bridge.service, ps aux | grep agy.")
    if ctx:
        try:
            ctx.notify(msg)
        except Exception:
            pass
    return msg


def run(ctx=None):
    stale = check_stale_claims()
    epic_flags = check_parent_sync()
    stale_notes = check_stale_notes()
    red_ci = check_red_ci_review()
    health = check_bridge_health(ctx)

    lines = []
    if stale:
        lines.append(f"🏴 claim yatim diflag: {', '.join(stale)}")
    if epic_flags:
        lines.append(f"🔄 EPIC perlu dicek: {', '.join(epic_flags)}")
    if stale_notes:
        lines.append(f"📝 notes basi diflag: {', '.join(stale_notes)}")
    if red_ci:
        lines.append(f"🔴 CI merah di review: {', '.join(red_ci)}")
    if health:
        lines.append(health)
    report = "\n".join(lines) if lines else "audit: board konsisten, tidak ada temuan."
    print(report)
    if lines and ctx is not None:
        try:
            ctx.notify(report)
        except Exception:
            pass
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "run":
        sys.exit(__doc__)
    run()
