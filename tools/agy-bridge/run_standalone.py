#!/usr/bin/env python3
"""Standalone runner for the board -> agy bridge, independent of KiroCrew gateway.

The canonical bridge (`board_agy_bridge.py`) was written to be driven by a
KiroCrew `script` cron, which injects a ScriptContext (`ctx`). The ONLY thing it
uses from ctx is `ctx.notify(report)` on a real signal (one place, line ~353).
Everything else (scan board, call agy via subprocess, verify PR, auto-unblock,
account rotation, write reports, advance status) is plain Python with no gateway
dependency.

So this runner supplies a minimal ctx shim and calls the same `run(ctx)` — zero
logic duplicated. Driven by a systemd user timer (see agy-bridge.timer), it runs
every 5 minutes 24/7 WITHOUT the KiroCrew gateway being up.

Notifications: ctx.notify() here appends to a log file and (best-effort) fires a
desktop `notify-send`. It never touches the KiroCrew bell — that path needs the
gateway and is intentionally dropped in standalone mode.
"""
import datetime
import importlib.util
import shutil
import subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CANON = _HERE / "board_agy_bridge.py"
_LOG = Path.home() / "Apps" / "board" / "tools" / "agy-bridge" / "bridge.log"


def _load_bridge():
    spec = importlib.util.spec_from_file_location("board_agy_bridge_canon", str(_CANON))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _StandaloneCtx:
    """Minimal stand-in for KiroCrew's ScriptContext.

    The bridge only calls ctx.notify(); message is unused in code. We log every
    real signal and best-effort surface a desktop notification.
    """

    message = ""

    def notify(self, text, title="agy bridge"):
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            _LOG.parent.mkdir(parents=True, exist_ok=True)
            with _LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"\n===== {stamp} =====\n{text}\n")
        except Exception:
            pass
        notify = shutil.which("notify-send")
        if notify:  # desktop toast when a GUI session is present; harmless headless
            try:
                subprocess.run([notify, title, text[:400]], timeout=5, check=False)
            except Exception:
                pass


def main():
    ctx = _StandaloneCtx()
    try:
        result = _load_bridge().run(ctx)
    except Exception as exc:  # a crash must be logged, not silent, for a 24/7 timer
        ctx.notify(f"[bridge CRASHED] {type(exc).__name__}: {exc}")
        raise
    # Quiet scans ("tidak ada task agy status=todo") return a short string and are
    # NOT notified — only real signals go through ctx.notify() inside run().
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with _LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] poll: {result}\n")
    except Exception:
        pass
    print(result)


if __name__ == "__main__":
    main()
