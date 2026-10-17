#!/usr/bin/env bash
# agy-snapshot-account.sh N
#
# Save the CURRENTLY logged-in agy account's OAuth token as snapshot acctN.json.
# Run this ONCE per PRO account, after you log that account in via browser:
#
#   1. agy  (interactive) → log in to PRO account #1 via browser
#   2. ./agy-snapshot-account.sh 1
#   3. log out / switch, log in PRO account #2
#   4. ./agy-snapshot-account.sh 2
#   ... up to how many accounts you have (e.g. 5)
#
# Rotation then swaps these snapshots automatically when a 5-hour limit hits.
set -euo pipefail

N="${1:-}"
if ! [[ "$N" =~ ^[0-9]+$ ]]; then
  echo "usage: $0 <account-number>   (e.g. $0 1)" >&2
  exit 2
fi

LIVE="$HOME/.gemini/antigravity-cli/antigravity-oauth-token"
DIR="$HOME/Apps/credentials/agy"
DEST="$DIR/acct${N}.json"

if [[ ! -f "$LIVE" ]]; then
  echo "ERROR: tidak ada token login aktif di $LIVE — login agy dulu." >&2
  exit 1
fi
# sanity: must be the consumer OAuth JSON agy writes
if ! python3 -c "import json,sys; d=json.load(open('$LIVE')); assert 'token' in d and 'refresh_token' in d['token']" 2>/dev/null; then
  echo "ERROR: $LIVE bukan token OAuth agy yang valid (tak ada refresh_token)." >&2
  exit 1
fi

mkdir -p "$DIR"
  chmod 700 "$DIR" 2>/dev/null || true
cp -p "$LIVE" "$DEST"
chmod 600 "$DEST"
echo "✓ snapshot akun $N tersimpan: $DEST"
echo "  snapshot sekarang: $(ls "$DIR"/acct*.json 2>/dev/null | xargs -n1 basename | tr '\n' ' ')"
