#!/usr/bin/env python3
"""Self-check for board_switch.py (no network, no real board): python3 test_board_switch.py"""
import json
import tempfile
from pathlib import Path

import board_agy_bridge as B
import board_switch as S

tmp = Path(tempfile.mkdtemp())
(tmp / "tasks").mkdir()
B._active_task_files = lambda: sorted((tmp / "tasks").glob("*.json"))
B._log_event = lambda *a, **k: None
tries = {}
B._retry_state = lambda k: (tries.get(k, 0), None)
B._retry_bump = lambda k, e="": tries.__setitem__(k, tries.get(k, 0) + 1)


def task(tid, status, branch="feat/x", **extra):
    t = {"id": tid, "type": "task", "title": tid, "status": status, "assignee": "agy",
         "description": f"BRANCH {branch}", **extra}
    (tmp / "tasks" / f"{tid}.json").write_text(json.dumps(t))


def status(tid):
    return json.loads((tmp / "tasks" / f"{tid}.json").read_text())["status"]


pr = {"number": 7, "state": "OPEN", "headRefOid": "a" * 40}
ci = ("failure", ["Lint"], tmp)
B._branch_pr = lambda branch: pr
B._ci_state = lambda p: ci

task("TASK-1", "review")
S.review()                               # CI red, attempt 1 -> back to todo
assert status("TASK-1") == "todo", status("TASK-1")

task("TASK-1", "review")
S.review(); task("TASK-1", "review"); S.review()   # attempts 2 and 3
assert status("TASK-1") == "todo" and tries["ci-pr-7"] == 3
task("TASK-1", "review")
S.review()                               # attempt 4 -> limit -> blocked for a human
assert status("TASK-1") == "blocked", status("TASK-1")

for state, want in (("success", "review"), ("pending", "review"), (None, "review")):
    ci = (state, [], tmp)
    task("TASK-2", "review"); S.review()
    assert status("TASK-2") == want, (state, status("TASK-2"))

# CI trigger: only a head without a final verdict starts CI; green and red never do.
task("TASK-2", "done")      # leftover from the loop above; keep this block self-contained
task("TASK-1", "done")      # _prime_ci() starts CI for any non-review/non-done task with an open PR
started = []
B._trigger_ci = lambda n, sha: started.append((n, sha))
for state, want in (("success", 0), ("failure", 0), (None, 1), ("pending", 1), ("error", 1)):
    started.clear(); tries.clear(); ci = (state, ["Lint"] if state == "failure" else [], tmp)
    task("TASK-6", "review"); S.review()
    assert len(started) == want, (state, started)
    if want:
        assert started[0] == (7, "a" * 40) and status("TASK-6") == "review"
tries.clear(); started.clear(); ci = ("error", [], tmp)
for _ in range(S.MAX_CI_ERROR_RETRY + 2):                      # error restarts stop after the cap
    task("TASK-6", "review"); S.review()
assert len(started) == S.MAX_CI_ERROR_RETRY, started
B._retry_state = lambda k: (tries.get(k, 0), B._now())          # just retried: backoff holds the next one
tries.clear(); started.clear(); task("TASK-6", "review"); S.review()
assert started == [], started
B._retry_state = lambda k: (tries.get(k, 0), None)

pr = {"number": 8, "state": "MERGED", "headRefOid": "b" * 40}
task("TASK-3", "review"); S.review()
assert status("TASK-3") == "done"

pr = {"number": 9, "state": "CLOSED", "headRefOid": "c" * 40}
task("TASK-4", "review"); S.review()
assert status("TASK-4") == "blocked"

task("TASK-5", "in-progress"); S.review()    # only `review` tasks are touched
assert status("TASK-5") == "in-progress"
print("board_switch: all checks passed")
