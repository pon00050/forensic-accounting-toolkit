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
echo "Run /triage for full task scan across all 10 sources."
