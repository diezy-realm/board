#!/usr/bin/env python3
"""Board -> agy (Antigravity) bridge, run by a KiroCrew cron as a `script` job.

Scans the shared board for tasks assigned to agy that are ready to run, executes
each one by calling the agy CLI headless. The FIRST wake of a task runs a clean
session; a task that spans several wakes RESUMES the same agy conversation
(`--conversation <id>`, i.e. -c) so its accumulated context (and the one-time
onboarding of GEMINI.md/AGENTS.md) carries over instead of paying a cold restart
each wake. Writes a Report and advances the task status. Deterministic, no LLM
in the loop.

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
import sqlite3
import fcntl

HOME = Path.home()
BOARD = HOME / "Apps" / "board"
GALLEON = HOME / "Apps" / "galleon-fleet"
AGY = HOME / ".local" / "bin" / "agy"

# Shared event DB: bridge WRITES completion/retry events here; the board server
# READS it for the bell dropdown. Single source of truth for "what finished".
BRIDGE_DB = HOME / "Apps" / "board" / "tools" / "agy-bridge" / "bridge_events.db"
EVENT_TTL_DAYS = 7            # auto-remove events older than H+7


def _db():
    BRIDGE_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(BRIDGE_DB), timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
        kind TEXT NOT NULL, task_id TEXT, title TEXT, report TEXT, detail TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS retries(
        task_id TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0,
        last_attempt TEXT, last_error TEXT)""")
    return c


def _log_event(kind, task_id="", title="", report="", detail=""):
    try:
        c = _db()
        c.execute("INSERT INTO events(ts,kind,task_id,title,report,detail) VALUES(?,?,?,?,?,?)",
                  (_now(), kind, task_id, title, report, detail[:500]))
        # H+7 purge on every write (cheap, deterministic)
        cutoff = (datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(days=EVENT_TTL_DAYS)).isoformat()
        c.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
        c.commit(); c.close()
    except Exception:
        pass


def _retry_state(task_id):
    try:
        c = _db()
        row = c.execute("SELECT count,last_attempt FROM retries WHERE task_id=?",
                        (task_id,)).fetchone()
        c.close()
        return (row[0], row[1]) if row else (0, None)
    except Exception:
        return (0, None)


def _retry_bump(task_id, err=""):
    try:
        c = _db()
        n, _ = _retry_state(task_id)
        c.execute("""INSERT INTO retries(task_id,count,last_attempt,last_error)
                     VALUES(?,?,?,?)
                     ON CONFLICT(task_id) DO UPDATE SET
                       count=count+1, last_attempt=excluded.last_attempt,
                       last_error=excluded.last_error""",
                  (task_id, n + 1, _now(), err[:300]))
        c.commit(); c.close()
    except Exception:
        pass


# account-rotation TOOLING lives in the board (general agy tooling, not KiroCrew);
# token STATE stays private under ~/.kiro/crew/agy-accounts/ (never web-served).
_ROTATE_TOOL = HOME / "Apps" / "board" / "tools" / "agy-rotate"
if str(_ROTATE_TOOL) not in sys.path:
    sys.path.insert(0, str(_ROTATE_TOOL))
try:
    import agy_rotate as _agy_rotate
except Exception:
    _agy_rotate = None  # rotation unavailable → bridge still works, just no rotate

# agy runs ONE task per wake, serially (systemd timer never overlaps). We let agy
# finish on its own (`--print-timeout 0`); no per-task wall. The only safety net is
# systemd TimeoutStartSec, which kills a genuinely WEDGED run — not normal long work.
MAX_TASKS_PER_WAKE = 1       # serialize: one agy run per poll, avoids parallel writers
_LAST_CONV_ID = None         # set by _run_agy from the JSON envelope each run


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _is_sprint_active(sprint_dir: Path) -> bool:
    """Returns True ONLY if SPRINT.md explicitly declares status: active."""
    sp = sprint_dir / "SPRINT.md"
    if not sp.is_file():
        return False
    try:
        text = sp.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("status:"):
                val = line.split(":", 1)[1].strip().lower()
                return val == "active"
    except Exception:
        return False
    return False


def _active_task_files():
    """Task JSONs in an ACTIVE sprint tasks/ folder only."""
    out = []
    if not BOARD.is_dir():
        return out
    for f in sorted(BOARD.rglob("*.json")):
        rel = f.relative_to(BOARD).parts
        if f.parent.name == "tasks" and "archive" not in rel:
            sprint_dir = f.parent.parent
            if _is_sprint_active(sprint_dir):
                out.append(f)
    return out


def _live_task_files():
    """All task JSONs in any non-archived sprint folder (active or planning)."""
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
    """RPT-NNN unique across the whole board (ids never reused).
    Uses file lock to prevent race condition when multiple processes scan simultaneously."""
    lock_file = BOARD / ".rpt_id_lock"
    # Acquire exclusive lock (blocks if another process holds it)
    with open(str(lock_file), "a") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            nums = [0]
            for f in BOARD.rglob("RPT-*.md"):
                m = re.match(r"RPT-(\d+)", f.stem)
                if m:
                    nums.append(int(m.group(1)))
            return f"RPT-{max(nums) + 1:03d}"
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


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


def _run_agy(description, conversation_id=None):
    """Call agy headless. Returns (ok, text, is_limit). cwd=board; both dirs on workspace.
    is_limit=True means the failure looks like a 5-hour/weekly PRO usage limit
    (candidate for account rotation), not a real task error.
    conversation_id: when set, resume that agy conversation (-c continuation for a
    task spanning several wakes) instead of a clean session.
    No per-task timeout: agy finishes on its own (`--print-timeout 0`); systemd
    TimeoutStartSec is the only safety net against a genuinely wedged run."""
    if not AGY.exists():
        return False, f"agy CLI tidak ditemukan di {AGY}", False
    cmd = [
        str(AGY), "--dangerously-skip-permissions",
        "--add-dir", str(BOARD),
        "--add-dir", str(GALLEON),
    ]
    if conversation_id:
        cmd += ["--conversation", str(conversation_id)]  # resume same session
    cmd += [
        "-p", description,
        "--output-format", "json",
        "--print-timeout", "0s",   # 0 = wait until the turn completes
    ]
    try:
        p = subprocess.run(cmd, cwd=str(BOARD), capture_output=True, text=True)
    except Exception as e:
        return False, f"agy gagal dijalankan: {e}", False
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        combined = f"agy exit {p.returncode}\nSTDERR:\n{err[:2000]}\nSTDOUT:\n{out[:1000]}"
        is_limit = False
        try:
            is_limit = _agy_rotate.is_limit_error(err + "\n" + out)
        except Exception:
            pass
        # even a timeout/non-zero exit still printed the JSON envelope with the
        # conversation_id — stash it so the next wake can resume (-c).
        try:
            cid = json.loads(out).get("conversation_id") if out.strip().startswith("{") else None
            if cid:
                globals()["_LAST_CONV_ID"] = cid
        except Exception:
            pass
        return False, combined, is_limit
    # agy --output-format json emits a JSON envelope; extract a human text if present
    text = out
    try:
        j = json.loads(out)
        text = j.get("result") or j.get("text") or j.get("response") or out
        cid = j.get("conversation_id")
        if cid:
            globals()["_LAST_CONV_ID"] = cid   # stash: the stripped text loses it
    except Exception:
        pass
    return True, text or "(agy tidak mengembalikan teks)", False


def _expected_branch(task: dict) -> str:
    """Pull the branch name agy is told to use from the task (feat/... token)."""
    import re as _re
    blob = (task.get("description", "") or "") + " " + " ".join(task.get("acceptance") or [])
    m = _re.search(r"[Bb]ranch:\s*(feat/[A-Za-z0-9._/-]+)", blob)
    if m:
        return m.group(1).rstrip(".,);")
    m = _re.search(r"feat/[A-Za-z0-9._/-]+", blob)
    return m.group(0).rstrip(".,);") if m else ""


def _verify_agy_delivered(task: dict, agy_text: str = "") -> tuple:
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
            # Distinguish a genuine push failure from agy DELIBERATELY declining
            # because a PRASYARAT predecessor isn't merged yet — agy says so in
            # its own output. That is correct sequencing, not a failure to fix.
            low = (agy_text or "").lower()
            if "blocked" in low and ("prasyarat" in low or "sequencing" in low
                                     or "belum terpenuhi" in low or "belum merged" in low):
                return False, (f"agy menolak jalan: prasyarat belum merged "
                               f"(branch {branch} belum dibuat — sequencing, bukan gagal)")
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


def _run_agy_with_rotation(description, max_rotations=5, conversation_id=None):
    """Run agy; on a usage-limit failure, mark the account limited, rotate to the
    next available PRO account, and retry the SAME task (idempotent run).
    Returns (ok, text). Falls back to blocked when every account is cooling down."""
    if _agy_rotate is None:
        ok, text, _ = _run_agy(description, conversation_id)
        return ok, text
    text = ""
    for _ in range(max_rotations + 1):
        ok, text, is_limit = _run_agy(description, conversation_id)
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


def _branch_pr(branch: str):
    """Newest PR (any state) whose head is `branch`: {number,state,headRefOid,baseRefName} or None."""
    if not branch:
        return None
    try:
        r = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "all", "--json",
                            "number,state,headRefOid,baseRefName", "--limit", "1"],
                           cwd=str(GALLEON), capture_output=True, text=True, timeout=60)
        prs = json.loads(r.stdout or "[]")
        return prs[0] if prs else None
    except Exception:
        return None


# Local CI (~/Apps/dev-ci/bin/ci-poller) publishes commit statuses `local/<gate>` plus the
# aggregate `local/Required Gate`, and a summary.json + per-gate logs per PR head SHA.
DEVCI_LOGS = HOME / "Apps" / "dev-ci" / "logs" / "galleon-fleet"
CI_AGG = "local/Required Gate"
_CI_POLLER = HOME / "Apps" / "dev-ci" / "bin" / "ci-poller"


def _trigger_ci(pr_number, sha):
    """Start local CI for one PR head as the transient user unit `ci-pr<N>-<sha8>`. Own cgroup, so it
    outlives the oneshot board service that calls this; the unit name rejects a second start while one
    is queued or running. ci-poller's blocking flock queues distinct runs. True if a unit was started."""
    if not pr_number or not sha or not _CI_POLLER.exists():
        return False
    r = subprocess.run(["systemd-run", "--user", "--quiet", "--collect", f"--unit=ci-pr{pr_number}-{sha[:8]}",
                        f"--setenv=PATH={HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin",
                        "/usr/bin/python3", str(_CI_POLLER), "galleon-fleet", "--pr", str(pr_number)],
                       capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def _ci_state(pr: dict):
    """(aggregate state or None, [red required gate names], log dir) for the PR's head SHA.
    State is success|failure|error|pending, or None while CI has not reported yet."""
    sha = pr.get("headRefOid", "")
    logdir = DEVCI_LOGS / f"pr{pr.get('number')}-{sha[:8]}"
    try:
        r = subprocess.run(["gh", "api", f"repos/{{owner}}/{{repo}}/commits/{sha}/status?per_page=100"],
                           cwd=str(GALLEON), capture_output=True, text=True, timeout=60)
        agg = next((x for x in json.loads(r.stdout)["statuses"] if x["context"] == CI_AGG), None)
    except Exception:
        return None, [], logdir
    if not agg:
        return None, [], logdir
    red = []
    try:
        red = json.loads((logdir / "summary.json").read_text()).get("red", [])
    except Exception:
        pass
    return agg["state"], red, logdir


def _log_tail(path, lines=40, cap=3500):
    try:
        return "\n".join(Path(path).read_text(errors="replace").splitlines()[-lines:])[-cap:]
    except Exception:
        return "(log tidak terbaca)"


def _continuation_block(task: dict) -> str:
    """Prompt prefix for a task whose branch already has an OPEN PR (CI red or sent back from
    review): continue on that branch instead of starting over."""
    branch = _expected_branch(task)
    pr = _branch_pr(branch)
    if not pr or pr.get("state") != "OPEN":
        return ""
    out = [f"PR #{pr['number']} SUDAH ADA untuk branch {branch} (base {pr.get('baseRefName')}). "
           f"Lanjutkan di branch itu: checkout, perbaiki, commit + push ke branch yang SAMA. "
           f"JANGAN buat branch atau PR baru, JANGAN merge."]
    state, red, logdir = _ci_state(pr)
    if state == "failure":
        out.append(f"CI lokal MERAH pada head {pr['headRefOid'][:8]}. Gate wajib yang gagal: {', '.join(red) or '?'}.")
        for name in red[:3]:
            slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            out.append(f"--- log {name} ({logdir / (slug + '.log')}), 40 baris terakhir:\n"
                       + _log_tail(logdir / f"{slug}.log"))
    return "\n".join(out) + "\n\n"


def run(ctx):
    msg = (getattr(ctx, "message", "") or "").strip()

    if not BOARD.is_dir():
        return f"board tidak ada di {BOARD} — tidak ada yang discan."

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
        prompt = _continuation_block(t) + desc
        if acc:
            prompt += "\n\nKriteria penerimaan (acceptance):\n" + "\n".join(f"- {a}" for a in acc)
        prompt += ("\n\nKonteks: kamu dipanggil oleh bridge koordinasi dari papan kerja "
                   f"~/Apps/board (lihat RULES.md). Kerjakan task {tid} ini sampai selesai, "
                   "lalu ringkas hasil + bukti nyata (path file/commit). "
                   "Jika pekerjaan belum tuntas saat waktu hampir habis: COMMIT + PUSH progres "
                   "parsial ke branch + catat sisa, JANGAN akhiri dengan 'will wait'.")

        # point c+d: a big task spanning several wakes resumes the SAME agy
        # conversation (-c) so accumulated context carries over across wakes.
        prev_conv = t.get("agy_conversation_id") or None
        globals()["_LAST_CONV_ID"] = None  # reset; _run_agy sets it from the envelope
        ok, text = _run_agy_with_rotation(prompt, conversation_id=prev_conv)
        # persist the conversation id agy reported (stashed by _run_agy from the raw
        # JSON envelope — the returned text strips it), so next wake resumes it.
        _conv = globals().get("_LAST_CONV_ID") or prev_conv
        if _conv:
            t = _load(f) or t
            t["agy_conversation_id"] = _conv
            _save(f, t)
        rpt_id = _next_report_id(sprint_dir)
        # A success claim is only accepted if agy actually delivered a PR/branch.
        if ok:
            delivered, detail = _verify_agy_delivered(t, text)
            if not delivered:
                ok = False
                text = (f"agy tidak mengirim hasil: {detail}. Output agy:\n{text[:800]}")
        if ok:
            _write_report(sprint_dir, rpt_id, t, "done", text[:600], text)
            # PR still open -> `review` (board_switch.py review decides done / back to todo)
            pr = _branch_pr(_expected_branch(t))
            new_status = "review" if pr and pr.get("state") == "OPEN" else "done"
            t = _load(f) or t
            t["status"] = new_status
            t["report"] = rpt_id
            t["updated"] = _now()
            _save(f, t)
            processed.append(f"{tid} -> {new_status} ({rpt_id}; {detail})")
            _log_event(new_status, tid, t.get("title", ""), report=rpt_id, detail=detail)
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
            _log_event("blocked", tid, t.get("title", ""), report=rpt_id, detail=text[:300])

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
