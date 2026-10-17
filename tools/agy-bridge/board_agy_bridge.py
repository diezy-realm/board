#!/usr/bin/env python3
"""Board -> agy (Antigravity) bridge, run by a KiroCrew cron as a `script` job.

Scans the shared board for tasks assigned to agy that are ready to run, executes
each one by calling the agy CLI headless (single-shot `-p`, NOT `-c`), writes a
Report, and advances the task status. Deterministic, no LLM in the loop.

Contract (per ~/Apps/board/RULES.md §5):
  pick tasks where assignee == "agy" and status == "todo"
  -> set status "in-progress" (claim, so a second poll won't double-run)
  -> run: agy --dangerously-skip-permissions -p "<description>" --output-format json
          (cwd = board, --add-dir board + galleon-fleet so agy can read both)
  -> write reports/RPT-NNN.md (source_task), set task status "done" + report: RPT-NNN
  -> on failure: status "blocked", notes = reason (no hang, bounded by timeout)

Register (one-off, from the dashboard or chat):
  cron_add(name="board-agy-bridge",
           script="~/.kiro/crew/crons/board_agy_bridge.py:run",
           every=300, persistent_session=False, minimal_context=True,
           hide_in_chat=True, silent=True)

The ScriptContext (`ctx`) gives ctx.message, ctx.notify(), and Skip/Done/Report.
We only ctx.notify() on real signals (a task ran, or one got blocked); a quiet
scan returns a short string and posts nothing.
"""
import json
import re
import sys
import subprocess
import datetime
from pathlib import Path

HOME = Path.home()
BOARD = HOME / "Apps" / "board"
GALLEON = HOME / "Apps" / "galleon-fleet"
AGY = HOME / ".local" / "bin" / "agy"

# account-rotation TOOLING lives in the board (general agy tooling, not KiroCrew);
# token STATE stays private under ~/.kiro/crew/agy-accounts/ (never web-served).
_ROTATE_TOOL = HOME / "Apps" / "board" / "tools" / "agy-rotate"
if str(_ROTATE_TOOL) not in sys.path:
    sys.path.insert(0, str(_ROTATE_TOOL))
try:
    import agy_rotate as _agy_rotate
except Exception:
    _agy_rotate = None  # rotation unavailable → bridge still works, just no rotate

# One agy run gets this many seconds before we give up and mark the task blocked.
PER_TASK_TIMEOUT = 1500  # < cron timeout_secs default 1800, leaves headroom
MAX_TASKS_PER_WAKE = 1   # serialize: one agy run per poll, avoids parallel writers


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _active_task_files():
    """Task JSONs in a live (non-archived) sprint tasks/ folder."""
    out = []
    if not BOARD.is_dir():
        return out
    for f in sorted(BOARD.rglob("*.json")):
        rel = f.relative_to(BOARD).parts
        if f.parent.name == "tasks" and "archive" not in rel:
            out.append(f)
    return out


def _load(f):
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save(f, obj):
    f.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_report_id(sprint_dir):
    """RPT-NNN unique across the whole board (ids never reused)."""
    nums = [0]
    for f in BOARD.rglob("RPT-*.md"):
        m = re.match(r"RPT-(\d+)", f.stem)
        if m:
            nums.append(int(m.group(1)))
    return f"RPT-{max(nums) + 1:03d}"


def _write_report(sprint_dir, rpt_id, task, status, summary, evidence):
    rdir = sprint_dir / "reports"
    rdir.mkdir(parents=True, exist_ok=True)
    acc = task.get("acceptance") or []
    acc_lines = "\n".join(f"- [{'x' if status == 'done' else ' '}] {a}" for a in acc) or "- [ ] (tidak ada acceptance eksplisit di task)"
    body = f"""---
id: {rpt_id}
type: report
title: {task.get('title', task.get('id', ''))}
status: {status}
source_task: {task.get('id', '')}
author: agy
created: {_now()[:10]}
---
## Ringkasan
{summary}

## Yang Dikerjakan
Dieksekusi otomatis oleh bridge KiroCrew -> agy (headless, sesi bersih `-p`).

## Bukti (Evidence)
```
{evidence[:4000]}
```

## Cek Penerimaan (Acceptance Check)
{acc_lines}

## Catatan / Lanjutan
{'Task selesai sesuai instruksi.' if status == 'done' else 'Lihat bukti di atas; task ditandai ' + status + ' untuk ditinjau KiroCrew.'}
"""
    (rdir / f"{rpt_id}.md").write_text(body, encoding="utf-8")
    return rdir / f"{rpt_id}.md"


def _run_agy(description):
    """Call agy headless. Returns (ok, text, is_limit). cwd=board; both dirs on workspace.
    is_limit=True means the failure looks like a 5-hour/weekly PRO usage limit
    (candidate for account rotation), not a real task error."""
    if not AGY.exists():
        return False, f"agy CLI tidak ditemukan di {AGY}", False
    cmd = [
        str(AGY), "--dangerously-skip-permissions",
        "--add-dir", str(BOARD),
        "--add-dir", str(GALLEON),
        "-p", description,
        "--output-format", "json",
        "--print-timeout", f"{PER_TASK_TIMEOUT}s",
    ]
    try:
        p = subprocess.run(cmd, cwd=str(BOARD), capture_output=True, text=True,
                           timeout=PER_TASK_TIMEOUT + 30)
    except subprocess.TimeoutExpired:
        return False, f"agy timeout setelah {PER_TASK_TIMEOUT}s", False
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        combined = f"agy exit {p.returncode}\nSTDERR:\n{err[:2000]}\nSTDOUT:\n{out[:1000]}"
        is_limit = False
        try:
            is_limit = _agy_rotate.is_limit_error(err + "\n" + out)
        except Exception:
            pass
        return False, combined, is_limit
    # agy --output-format json emits a JSON envelope; extract a human text if present
    text = out
    try:
        j = json.loads(out)
        text = j.get("result") or j.get("text") or j.get("response") or out
    except Exception:
        pass
    return True, text or "(agy tidak mengembalikan teks)", False


def _expected_branch(task: dict) -> str:
    """Pull the branch name agy is told to use from the task (feat/... token)."""
    import re as _re
    blob = (task.get("description", "") or "") + " " + " ".join(task.get("acceptance") or [])
    m = _re.search(r"feat/[A-Za-z0-9._/-]+", blob)
    return m.group(0).rstrip(".,);") if m else ""


def _verify_agy_delivered(task: dict) -> tuple:
    """A 'done' claim is only real if agy actually PUSHED its branch and opened a
    PR to testing. agy running `cargo check` in the background then ending its
    `-p` turn with 'will wait' exits 0 but delivers nothing — this catches that.
    Returns (delivered, detail)."""
    branch = _expected_branch(task)
    if not branch:
        # no branch convention in task -> can't verify, accept (non-code tasks like steering)
        return True, "no branch to verify (non-PR task)"
    try:
        r = subprocess.run(["git", "ls-remote", "--heads", "origin", branch],
                           cwd=str(GALLEON), capture_output=True, text=True, timeout=60)
        if branch not in (r.stdout or ""):
            return False, f"branch {branch} belum di-push ke origin"
        pr = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "all",
                             "--json", "number,state", "--limit", "1"],
                            cwd=str(GALLEON), capture_output=True, text=True, timeout=60)
        prs = json.loads(pr.stdout or "[]")
        if not prs:
            return False, f"branch {branch} ada tapi TIDAK ada PR"
        return True, f"PR #{prs[0]['number']} ({prs[0]['state']}) untuk {branch}"
    except Exception as e:
        return False, f"verifikasi PR gagal: {e}"


def _run_agy_with_rotation(description, max_rotations=5):
    """Run agy; on a usage-limit failure, mark the account limited, rotate to the
    next available PRO account, and retry the SAME task (idempotent -p run).
    Returns (ok, text). Falls back to blocked when every account is cooling down."""
    if _agy_rotate is None:
        ok, text, _ = _run_agy(description)
        return ok, text
    text = ""
    for _ in range(max_rotations + 1):
        ok, text, is_limit = _run_agy(description)
        if ok or not is_limit:
            return ok, text
        # limit hit → cool down current account, rotate, retry
        try:
            st = _agy_rotate._load_state()
            cur = st.get("active", 0)
            if cur:
                _agy_rotate.mark_limited(cur)
            rot_ok, rot_msg = _agy_rotate.rotate_to_next()
        except Exception as e:
            return False, f"{text}\n[rotasi gagal: {e}]"
        if not rot_ok:
            return False, f"limit akun tercapai & {rot_msg}\n{text[:300]}"
        # loop retries with the newly-activated account
    return False, f"limit tetap setelah {max_rotations} rotasi akun\n{text[:300]}"


def _prereq_task(task: dict) -> str:
    """Prerequisite task id named as 'PRASYARAT: TASK-NNN' in the description."""
    import re as _re
    m = _re.search(r"PRASYARAT:\s*(TASK-\d+)", task.get("description", "") or "")
    return m.group(1) if m else ""


def _branch_pr_merged(branch: str) -> bool:
    """True if the branch's PR to testing is MERGED."""
    if not branch:
        return False
    try:
        r = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "merged",
                            "--json", "number", "--limit", "1"],
                           cwd=str(GALLEON), capture_output=True, text=True, timeout=60)
        return bool(json.loads(r.stdout or "[]"))
    except Exception:
        return False


def _auto_unblock():
    """Flip blocked agy tasks to todo once their prerequisite task is done AND
    that predecessor's PR is merged into testing. Makes the sequenced chain
    self-advancing without manual intervention."""
    files = {}
    for f in _active_task_files():
        t = _load(f)
        if t:
            files[t.get("id")] = (f, t)
    for tid, (f, t) in files.items():
        if t.get("assignee") != "agy" or t.get("status") != "blocked":
            continue
        prereq = _prereq_task(t)
        if not prereq or prereq not in files:
            continue
        _, pt = files[prereq]
        if pt.get("status") != "done":
            continue
        # predecessor done — require its PR merged (same crate = avoid conflict)
        if not _branch_pr_merged(_expected_branch(pt)):
            continue
        t["status"] = "todo"
        t["updated"] = _now()
        notes = (t.get("notes") or "")
        t["notes"] = (notes + f" | auto-unblock {_now()[:16]}: {prereq} done+merged").strip(" |")
        _save(f, t)


def run(ctx):
    msg = (getattr(ctx, "message", "") or "").strip()

    if not BOARD.is_dir():
        return f"board tidak ada di {BOARD} — tidak ada yang discan."

    # auto-unblock: a sub-task gated on a predecessor (PRASYARAT: TASK-NNN) flips
    # blocked->todo once that predecessor is done AND its PR is merged. This is
    # what makes the chain fully-automated — no manual flip between sub-tasks.
    _auto_unblock()

    # find agy tasks ready to run
    ready = []
    for f in _active_task_files():
        t = _load(f)
        if t and t.get("assignee") == "agy" and t.get("status") == "todo":
            ready.append((f, t))

    if not ready:
        # quiet scan — no notification
        return "scan board: tidak ada task agy status=todo."

    processed, blocked = [], []
    for f, t in ready[:MAX_TASKS_PER_WAKE]:
        tid = t.get("id", f.stem)
        # claim: todo -> in-progress BEFORE running (so a concurrent poll skips it)
        t["status"] = "in-progress"
        t["updated"] = _now()
        _save(f, t)

        sprint_dir = f.parent.parent  # sprints/sprint-NN/
        desc = t.get("description", "")
        acc = t.get("acceptance") or []
        prompt = desc
        if acc:
            prompt += "\n\nKriteria penerimaan (acceptance):\n" + "\n".join(f"- {a}" for a in acc)
        prompt += ("\n\nKonteks: kamu dipanggil oleh bridge koordinasi dari papan kerja "
                   f"~/Apps/board (lihat RULES.md). Kerjakan task {tid} ini sampai selesai, "
                   "lalu ringkas hasil + bukti nyata (path file/commit).")

        ok, text = _run_agy_with_rotation(prompt)
        rpt_id = _next_report_id(sprint_dir)
        # A success claim is only accepted if agy actually delivered a PR/branch.
        if ok:
            delivered, detail = _verify_agy_delivered(t)
            if not delivered:
                ok = False
                text = (f"agy mengklaim selesai TAPI tidak mengirim hasil: {detail}. "
                        f"(kemungkinan agy menjalankan build di background lalu mengakhiri turn "
                        f"dengan 'will wait' tanpa commit/push/PR). Output agy:\n{text[:800]}")
        if ok:
            _write_report(sprint_dir, rpt_id, t, "done", text[:600], text)
            t = _load(f) or t
            t["status"] = "done"
            t["report"] = rpt_id
            t["updated"] = _now()
            _save(f, t)
            processed.append(f"{tid} -> done ({rpt_id}; {detail})")
        else:
            _write_report(sprint_dir, rpt_id, t, "failed", "Eksekusi agy gagal.", text)
            t = _load(f) or t
            t["status"] = "blocked"
            t["report"] = rpt_id
            notes = (t.get("notes") or "")
            t["notes"] = (notes + f" | bridge {_now()[:16]}: {text[:300]}").strip(" |")
            t["updated"] = _now()
            _save(f, t)
            blocked.append(f"{tid} -> blocked: {text[:120]}")

    lines = []
    if processed:
        lines.append("✅ selesai: " + "; ".join(processed))
    if blocked:
        lines.append("⚠ blocked: " + "; ".join(blocked))
    remaining = len(ready) - len(processed) - len(blocked)
    if remaining > 0:
        lines.append(f"({remaining} task agy menunggu poll berikutnya)")
    report = "\n".join(lines)

    # real signal -> notify
    try:
        ctx.notify(report)
    except Exception:
        pass
    return report
