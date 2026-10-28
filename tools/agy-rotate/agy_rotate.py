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
# Account-level failures that are NOT a usage/quota limit but still mean "this
# account cannot do the work right now, skip to the next one": e.g. "Eligibility
# Check failed: Your current account is not eligible for Antigravity. Verify
# your account to continue." (seen in production on a freshly-added account).
# Routed through the same is_limit_error()/rotation path as a real limit — the
# caller's response (rotate to next account) is identical either way — but kept
# as a separate pattern list since it is semantically a different failure, not
# a time-based reset.
INELIGIBLE_PATTERNS = [
    r"\beligibility check failed\b", r"\bnot eligible\b", r"\bverify your account\b",
    r"\baccount (is )?(suspended|disabled|restricted)\b",
]
# Lines that look limit-ish enough to LOG for review even if not matched above.
_MAYBE = re.compile(r"limit|quota|credit|exhaust|429|resource|rate|resets?", re.I)
_LIMIT_RE = re.compile("|".join(LIMIT_PATTERNS), re.I)
_INELIGIBLE_RE = re.compile("|".join(INELIGIBLE_PATTERNS), re.I)

# No reset timer applies to an ineligible account — it is not a quota that heals
# with time, it needs the human to verify/fix the account. Cool it down for a
# long, bounded window so rotation keeps skipping it without retrying forever,
# but still re-offers it eventually in case the user fixed it in the meantime.
INELIGIBLE_COOLDOWN_SECS = 24 * 3600

# "Resets in 18h30m20s" / "Resets in 54m" / "Resets in 2h" — agy's own quota
# messages vary (5-hour PRO window vs. a longer daily/weekly individual quota).
# Parse it when present instead of always assuming the 5-hour window, or an
# account marked limited for only 5h gets retried while its real quota is
# still exhausted (seen in production: "Individual quota reached ... Resets
# in 18h30m20s" — every account cooled down 5h, then failed again on retry).
_RESET_IN_RE = re.compile(r"resets?\s+in\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?", re.I)


def _parse_reset_secs(text: str) -> int | None:
    """Seconds until reset, parsed from a 'Resets in ...' phrase in agy's error
    output. None if no such phrase is found (caller falls back to COOLDOWN_SECS)."""
    if not text:
        return None
    m = _RESET_IN_RE.search(text)
    if not m or not any(m.groups()):
        return None
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    secs = h * 3600 + mi * 60 + s
    return secs if secs > 0 else None


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
    """True if agy output signals a usage/credit/rate limit, OR an account-level
    failure that also means 'skip this account, try the next one' (eligibility
    check failed, account suspended/disabled). Auto-learn: an error that smells
    limit-ish but doesn't match either is appended to UNMATCHED_LOG so the
    patterns can be tightened from real data."""
    if not text:
        return False
    if _LIMIT_RE.search(text) or _INELIGIBLE_RE.search(text):
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


def mark_limited(idx: int, error_text: str = "") -> None:
    """Record that account idx hit its limit now (start its cooldown).
    Priority: (1) an explicit 'Resets in ...' duration from agy's error text
    (e.g. an 18.5h individual-quota message); (2) an account-ineligible failure
    (eligibility check failed / suspended) gets the long INELIGIBLE_COOLDOWN_SECS
    instead of the short 5h usage-limit assumption, since that is not a quota
    that heals in 5h — retrying it that soon just fails again for the same
    account-level reason; (3) fallback to the 5-hour PRO window (COOLDOWN_SECS)."""
    if (secs := _parse_reset_secs(error_text)) is None:
        secs = INELIGIBLE_COOLDOWN_SECS if _INELIGIBLE_RE.search(error_text or "") else COOLDOWN_SECS
    st = _load_state()
    st.setdefault("cooldown", {})[str(idx)] = _now() + secs
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
