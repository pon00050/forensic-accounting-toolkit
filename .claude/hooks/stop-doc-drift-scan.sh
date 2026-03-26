#!/usr/bin/env bash
# stop-doc-drift-scan.sh — Run DOC DRIFT check at session end.
#
# Finds files with stale 'kr-forensic-finance' references (excluding
# historical rename notes in "Previously known as" lines).
# Output is printed once so the user sees it before the session closes.

BASE="/c/Users/pon00/Projects"
HUB="$BASE/forensic-accounting-toolkit"

stale_files=()
while IFS= read -r f; do
    # For each file containing kr-forensic-finance, check if any
    # occurrence is NOT in a "Previously known as" line
    non_historical=$(grep -c "kr-forensic-finance" "$f" 2>/dev/null || echo 0)
    historical=$(grep -c "Previously known as.*kr-forensic-finance" "$f" 2>/dev/null || echo 0)
    if [ "$non_historical" -gt "$historical" ]; then
        stale_files+=("${f#$BASE/}")
    fi
done < <(grep -rl "kr-forensic-finance" \
    "$BASE"/*/CLAUDE.md \
    "$BASE"/*/README.md \
    "$HUB"/*.conf \
    "$HUB"/ARCHITECTURE.md \
    "$HUB"/ECOSYSTEM.md \
    "$HUB"/WORKFLOW.md \
    "$HUB"/lessons.md \
    2>/dev/null | grep -v "\.git" | grep -v "reports/" | grep -v ".venv")

if [ "${#stale_files[@]}" -gt 0 ]; then
    echo "--- DOC DRIFT (session end) ---"
    echo "  ${#stale_files[@]} file(s) still contain stale 'kr-forensic-finance':"
    for f in "${stale_files[@]}"; do
        echo "    $f"
    done
    echo "  Fix before next session or run /triage to surface these."
    echo "---"
fi
