#!/usr/bin/env python3
"""Sprint manager — Scrum lifecycle for the board.

Commands:
  status [NN]           show task done/total per sprint (default: all active sprints)
  close NN              close sprint-NN: carry over unfinished tasks to next sprint,
                        then move the whole sprint folder to archive/.
  new NN [category]     scaffold sprints/sprint-NN with SPRINT.md + specs/tasks/reports.
  carryover NN          only move unfinished tasks of sprint-NN to the next sprint.

Rules enforced (see RULES.md):
  - A sprint is CLOSE-ABLE only when every task is 'done'. Unfinished tasks are
    carried over FIRST (so the sprint ends empty of open work), THEN archived.
  - Carry-over copies the task JSON into the next sprint, resets status to 'todo',
    stamps carried_from, and keeps the original in the archived sprint for history.
Zero deps. Run from anywhere; paths are absolute to the board.
"""
import json
import shutil
import sys
import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parent
SPRINTS = BOARD / "sprints"
ARCHIVE = BOARD / "archive"

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sprint_dir(nn): return SPRINTS / f"sprint-{int(nn):02d}"
def tasks_of(d): return sorted((d / "tasks").glob("*.json")) if (d / "tasks").is_dir() else []

def load_task(p):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None

def status(nn=None):
    dirs = [sprint_dir(nn)] if nn else sorted([d for d in SPRINTS.glob("sprint-*") if d.is_dir()])
    if not dirs:
        print("Tidak ada sprint aktif."); return
    for d in dirs:
        if not d.is_dir(): print(f"{d.name}: tidak ada"); continue
        ts = tasks_of(d)
        done = sum(1 for p in ts if (load_task(p) or {}).get("status") == "done")
        open_ = [p.name for p in ts if (load_task(p) or {}).get("status") != "done"]
        goal = ""
        sp = d / "SPRINT.md"
        if sp.is_file():
            for line in sp.read_text(encoding="utf-8").splitlines():
                if line.startswith("goal:"): goal = line.split(":",1)[1].strip(); break
        state = "ALL DONE ✅ (siap close)" if ts and done == len(ts) else f"{done}/{len(ts)} done"
        print(f"{d.name} — {state}  | goal: {goal}")
        if open_:
            print("   open:", ", ".join(open_))

def next_sprint_num(nn):
    return int(nn) + 1

def new_sprint(nn, category="(tentukan)"):
    d = sprint_dir(nn)
    for sub in ("specs", "tasks", "reports"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    sp = d / "SPRINT.md"
    if not sp.is_file():
        sp.write_text(f"""---
id: sprint-{int(nn):02d}
type: sprint
goal: (isi sprint goal)
category: {category}
status: active
start: {now()[:10]}
end:
author: kirocrew
---
# Sprint {int(nn):02d} — {category}

> **Sprint Goal:** (isi)

Task di `tasks/`, spec di `specs/`, report di `reports/`.
Aturan tutup & carry-over: lihat `../../RULES.md`.
""", encoding="utf-8")
    print(f"dibuat: {d.relative_to(BOARD)}")
    return d

def carryover(nn):
    d = sprint_dir(nn)
    ts = tasks_of(d)
    unfinished = [p for p in ts if (load_task(p) or {}).get("status") != "done"]
    if not unfinished:
        print("Tidak ada task carry-over (semua done)."); return []
    nxt = next_sprint_num(nn)
    nd = sprint_dir(nxt)
    if not nd.is_dir():
        new_sprint(nxt)
    moved = []
    for p in unfinished:
        t = load_task(p)
        t["status"] = "todo"
        t["carried_from"] = f"sprint-{int(nn):02d}"
        t["updated"] = now()
        (nd / "tasks" / p.name).write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
        moved.append(p.name)
    print(f"carry-over {len(moved)} task ke sprint-{nxt:02d}:", ", ".join(moved))
    return moved

def close(nn):
    d = sprint_dir(nn)
    if not d.is_dir():
        print(f"sprint-{int(nn):02d} tidak ada."); return
    ts = tasks_of(d)
    unfinished = [p for p in ts if (load_task(p) or {}).get("status") != "done"]
    if unfinished:
        print(f"⚠ {len(unfinished)} task belum done — carry-over dulu ke sprint berikutnya.")
        carryover(nn)
    # mark SPRINT.md closed
    sp = d / "SPRINT.md"
    if sp.is_file():
        txt = sp.read_text(encoding="utf-8")
        txt = txt.replace("status: active", "status: closed")
        if "end:" in txt and "\nend:\n" in txt or "end: \n" in txt:
            pass
        import re
        txt = re.sub(r"^end:.*$", f"end: {now()[:10]}", txt, count=1, flags=re.M)
        sp.write_text(txt, encoding="utf-8")
    # archive the whole folder
    ARCHIVE.mkdir(exist_ok=True)
    dest = ARCHIVE / d.name
    if dest.exists():
        dest = ARCHIVE / f"{d.name}.{int(datetime.datetime.now().timestamp())}"
    shutil.move(str(d), str(dest))
    print(f"✅ sprint-{int(nn):02d} ditutup & diarsipkan -> {dest.relative_to(BOARD)}")
    print("   (task yang belum done sudah di-carry-over sebelum diarsip)")

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "status":
        status(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "close":
        close(sys.argv[2])
    elif cmd == "new":
        new_sprint(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "(tentukan)")
    elif cmd == "carryover":
        carryover(sys.argv[2])
    else:
        print("perintah tidak dikenal:", cmd); print(__doc__); sys.exit(2)

if __name__ == "__main__":
    main()
