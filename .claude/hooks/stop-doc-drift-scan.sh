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
    # Count lines that have stale name but are NOT historical/meta references
    real_stale=$(grep "kr-forensic-finance" "$f" 2>/dev/null \
        | grep -v "Previously known as" \
        | grep -v '`kr-forensic-finance`' \
        | grep -v '"kr-forensic-finance"' \
        | wc -l | tr -d ' ')
    if [ "$real_stale" -gt 0 ]; then
        stale_files+=("${f#$BASE/}")
    fi
# Scope to ecosystem repos only (from ecosystem.conf ALL_REPOS)
ECOSYSTEM_REPOS=(
    forensic-accounting-toolkit kr-company-registry kr-trading-calendar kr-beneish
    kr-derivatives jfia-catalog jfia-forensic kr-enforcement-cases kr-forensic-core
    krff-shell kr-dart-pipeline kr-anomaly-scoring kr-stat-tests kr-real-estate
)
SCAN_TARGETS=()
for r in "${ECOSYSTEM_REPOS[@]}"; do
    [ -f "$BASE/$r/CLAUDE.md" ] && SCAN_TARGETS+=("$BASE/$r/CLAUDE.md")
    [ -f "$BASE/$r/README.md" ] && SCAN_TARGETS+=("$BASE/$r/README.md")
done
SCAN_TARGETS+=(
    "$HUB/ARCHITECTURE.md" "$HUB/ECOSYSTEM.md"
    "$HUB/WORKFLOW.md" "$HUB/lessons.md" "$HUB"/*.conf
)

done < <(grep -rl "kr-forensic-finance" "${SCAN_TARGETS[@]}" \
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
