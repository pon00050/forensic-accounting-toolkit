#!/bin/bash
# SessionStart hook: load lessons + quick triage scan (board + git hygiene + backlog)
# Output goes to Claude as context. Full scan available via /triage.

# Resolve hub directory from this script's location
HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Load operational lessons
LESSONS="$HUB/lessons.md"
if [ -f "$LESSONS" ]; then
    echo "--- LESSONS (operational rules from past sessions) ---"
    cat "$LESSONS"
    echo ""
fi

# Quick triage scan
bash "$HUB/triage-scan.sh" quick

echo ""

# Staleness check: warn if the open triage issue is from a prior day
if [ -n "${GH:-}" ]; then
    TRIAGE_TITLE=$("$GH" issue list --label agent:triage --state open --json title --jq '.[0].title' 2>/dev/null || true)
    if [ -n "$TRIAGE_TITLE" ]; then
        TRIAGE_DATE=$(echo "$TRIAGE_TITLE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || true)
        TODAY=$(date '+%Y-%m-%d')
        if [ -n "$TRIAGE_DATE" ] && [ "$TRIAGE_DATE" != "$TODAY" ]; then
            echo "--- STALE TRIAGE ---"
            echo "  Open triage issue is from $TRIAGE_DATE (today: $TODAY)"
            echo "  Run /triage for current data, or trigger tier2-triage workflow."
            echo "---"
            echo ""
        fi
    fi
fi

echo "Run /triage for full task scan across all 10 sources."
