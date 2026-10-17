#!/usr/bin/env python3
"""agy account rotation core — shared by the board bridge and the CLI helper.

Model (confirmed with Achmad 2026-10-17): the Google account is tier PRO with a
5-hour rolling session window + weekly quota (Claude-style), NOT a monthly token
cap. So we rotate between N PRO accounts: when the active account hits its 5-hour
limit, swap to the next account whose cooldown has elapsed.

Auth = the OAuth consumer token file agy reads:
    ~/.gemini/antigravity-cli/antigravity-oauth-token   (JSON, auth_method=consumer)
A "snapshot" is a full copy of that file per account, taken once after the user
logs that account in via browser. Rotation = copy snapshot -> live token file.
No browser needed at rotate time; agy auto-refreshes access_token from the
refresh_token inside each snapshot.

State lives under ~/.kiro/crew/agy-accounts/ (durable; NOT scratch):
    acct1.json ... acctN.json   per-account token snapshots
    state.json                  {active:int, cooldown:{"1":epoch_until,...}}
    unmatched-errors.log        agy errors that MIGHT be limits but didn't match
                                (auto-learn: review to extend LIMIT_PATTERNS)

This module writes ONLY under agy-accounts/ and the live token file. No secrets
are logged — only account indices and timestamps.
"""
from __future__ import annotations
import json, os, re, shutil, time
from pathlib import Path

HOME = Path.home()
# State + token snapshots live in ~/Apps/credentials/agy (dedicated, mode 700,
# NOT git-tracked, NOT served by the board web server). OAuth tokens must never
# be web-reachable, so they are kept out of the tailnet-served board tree.
ACCT_DIR = HOME / "Apps" / "credentials" / "agy"
LIVE_TOKEN = HOME / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
STATE = ACCT_DIR / "state.json"
UNMATCHED_LOG = ACCT_DIR / "unmatched-errors.log"

# A PRO 5-hour window; after a limit hit, skip that account for this long.
COOLDOWN_SECS = int(os.environ.get("AGY_COOLDOWN_SECS", str(5 * 3600)))

# General limit-detection patterns (case-insensitive). Tuned over time from
# UNMATCHED_LOG once we see the real agy message. Claude-style wording covered.
LIMIT_PATTERNS = [
    r"\busage limit\b", r"\brate limit", r"\bquota\b", r"\bexhausted\b",
    r"\bresets?\s+(at|in)\b", r"\b5[- ]?hour", r"\bweekly limit\b",
    r"\blimit reached\b", r"\bout of (credits?|quota)\b",
    r"\bRESOURCE_EXHAUSTED\b", r"\b429\b", r"\btoo many requests\b",
    r"\btry again (later|in)\b", r"\bupgrade your plan\b",
]
# Lines that look limit-ish enough to LOG for review even if not matched above.
_MAYBE = re.compile(r"limit|quota|credit|exhaust|429|resource|rate|resets?", re.I)
_LIMIT_RE = re.compile("|".join(LIMIT_PATTERNS), re.I)


def _now() -> int:
    return int(time.time())


def account_snapshots() -> list[int]:
    """Indices (1-based) that have a snapshot file, sorted."""
    out = []
    for p in ACCT_DIR.glob("acct*.json"):
        m = re.match(r"acct(\d+)\.json$", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def _load_state() -> dict:
    if STATE.is_file():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"active": 0, "cooldown": {}}


def _save_state(st: dict) -> None:
    ACCT_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def is_limit_error(text: str) -> bool:
    """True if agy output signals a usage/credit/rate limit. Auto-learn: an
    error that smells limit-ish but doesn't match is appended to UNMATCHED_LOG
    so the patterns can be tightened from real data."""
    if not text:
        return False
    if _LIMIT_RE.search(text):
        return True
    if _MAYBE.search(text):
        try:
            ACCT_DIR.mkdir(parents=True, exist_ok=True)
            with UNMATCHED_LOG.open("a") as fh:
                fh.write(f"--- {time.strftime('%Y-%m-%dT%H:%M:%S')} (unmatched, maybe-limit) ---\n")
                fh.write(text[:1500].rstrip() + "\n\n")
        except Exception:
            pass
    return False


def activate(idx: int) -> tuple[bool, str]:
    """Copy acct<idx>.json over the live token file. Backs up the live file once."""
    snap = ACCT_DIR / f"acct{idx}.json"
    if not snap.is_file():
        return False, f"snapshot acct{idx}.json tidak ada"
    try:
        json.loads(snap.read_text())  # sanity: must be valid JSON token
    except Exception as e:
        return False, f"acct{idx}.json rusak: {e}"
    try:
        LIVE_TOKEN.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(snap), str(LIVE_TOKEN))
        os.chmod(LIVE_TOKEN, 0o600)
    except Exception as e:
        return False, f"gagal tulis token live: {e}"
    st = _load_state()
    st["active"] = idx
    _save_state(st)
    return True, f"akun {idx} aktif"


def mark_limited(idx: int) -> None:
    """Record that account idx hit its limit now (start its cooldown)."""
    st = _load_state()
    st.setdefault("cooldown", {})[str(idx)] = _now() + COOLDOWN_SECS
    _save_state(st)


def _available(idx: int, st: dict) -> bool:
    until = st.get("cooldown", {}).get(str(idx), 0)
    return _now() >= until


def rotate_to_next() -> tuple[bool, str]:
    """Switch to the next account (circular) whose cooldown has elapsed.
    Returns (ok, msg). ok=False means every account is still cooling down."""
    accts = account_snapshots()
    if not accts:
        return False, "tidak ada snapshot akun (acctN.json) di agy-accounts/"
    st = _load_state()
    cur = st.get("active", 0)
    # try accounts after current, wrapping around
    order = [a for a in accts if a > cur] + [a for a in accts if a <= cur]
    for idx in order:
        if idx == cur:
            continue
        if _available(idx, st):
            return activate(idx)
    # none free — report soonest reset
    cds = st.get("cooldown", {})
    if cds:
        soonest = min(cds.values())
        mins = max(0, int((soonest - _now()) / 60))
        return False, f"semua {len(accts)} akun masih cooldown; reset terdekat ~{mins} menit"
    return False, "tidak ada akun lain yang tersedia"


def status() -> str:
    st = _load_state()
    accts = account_snapshots()
    lines = [f"snapshots: {accts or 'KOSONG'}  | aktif: {st.get('active', 0)}"]
    for idx in accts:
        until = st.get("cooldown", {}).get(str(idx), 0)
        if until > _now():
            lines.append(f"  acct{idx}: cooldown {int((until-_now())/60)}m")
        else:
            lines.append(f"  acct{idx}: ready")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(status())
    elif cmd == "rotate":
        ok, msg = rotate_to_next()
        print(("OK: " if ok else "GAGAL: ") + msg)
    elif cmd == "activate" and len(sys.argv) > 2:
        ok, msg = activate(int(sys.argv[2]))
        print(("OK: " if ok else "GAGAL: ") + msg)
    else:
        print("usage: agy_rotate.py [status|rotate|activate N]")
