#!/usr/bin/env bash
# stop-board-snapshot.sh — Export board state to board-snapshot.json at session end.
#
# Committed to the hub repo so CI agents (which lack project scope on GITHUB_TOKEN)
# can read board state via board-snapshot.json instead of calling gh project live.
#
# Wired as a Stop hook in .claude/settings.json.
# Auto-stages the file if changed; does NOT auto-commit.

set -euo pipefail

HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$HUB/ecosystem.conf" 2>/dev/null || exit 0

# Skip if gh CLI not available
[ -z "${GH:-}" ] && exit 0

SNAPSHOT="$HUB/board-snapshot.json"

# Attempt live board export; exit silently if auth lacks project scope
BOARD_JSON=$("$GH" project item-list 1 --owner pon00050 --format json 2>/dev/null) || exit 0

# Validate: must be JSON with an 'items' key
echo "$BOARD_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert isinstance(d.get('items'), list), 'no items key'
" 2>/dev/null || exit 0

ITEM_COUNT=$(echo "$BOARD_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('items',[])))" 2>/dev/null || echo "?")

# Convert path for Python (Git Bash paths like /c/... are invalid on Windows Python)
WIN_SNAPSHOT=$(cygpath -w "$SNAPSHOT" 2>/dev/null || echo "$SNAPSHOT")

# Wrap with metadata and write (pipe BOARD_JSON as stdin so heredoc isn't needed)
echo "$BOARD_JSON" | python3 -c "
import json, sys
from datetime import datetime
raw = json.loads(sys.stdin.read())
snapshot = {
    'exported_at': datetime.now().isoformat(timespec='seconds'),
    'source': 'gh project item-list 1 --owner pon00050',
    'items': raw.get('items', [])
}
with open(sys.argv[1], 'w', encoding='utf-8', errors='replace') as f:
    json.dump(snapshot, f, indent=2, ensure_ascii=True)
" "$WIN_SNAPSHOT"

# Auto-stage if changed (user or /done handles the commit)
if ! git -C "$HUB" diff --quiet "$SNAPSHOT" 2>/dev/null || \
   ! git -C "$HUB" ls-files --error-unmatch "$SNAPSHOT" &>/dev/null 2>&1; then
    git -C "$HUB" add "$SNAPSHOT" 2>/dev/null || true
    echo "[board-snapshot] Updated board-snapshot.json ($ITEM_COUNT items)"
fi
