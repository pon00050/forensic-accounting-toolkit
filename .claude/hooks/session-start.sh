#!/bin/bash
# SessionStart hook: load lessons + quick triage scan (board + git hygiene + backlog)
# Output goes to Claude as context. Full scan available via /triage.

# Load operational lessons
LESSONS="C:/Users/pon00/Projects/forensic-accounting-toolkit/lessons.md"
if [ -f "$LESSONS" ]; then
    echo "--- LESSONS (operational rules from past sessions) ---"
    cat "$LESSONS"
    echo ""
fi

# Quick triage scan
bash "C:/Users/pon00/Projects/forensic-accounting-toolkit/triage-scan.sh" quick

echo ""
echo "Run /triage for full task scan across all 10 sources."
