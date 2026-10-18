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

pr = {"number": 8, "state": "MERGED", "headRefOid": "b" * 40}
task("TASK-3", "review"); S.review()
assert status("TASK-3") == "done"

pr = {"number": 9, "state": "CLOSED", "headRefOid": "c" * 40}
task("TASK-4", "review"); S.review()
assert status("TASK-4") == "blocked"

task("TASK-5", "in-progress"); S.review()    # only `review` tasks are touched
assert status("TASK-5") == "in-progress"
print("board_switch: all checks passed")
