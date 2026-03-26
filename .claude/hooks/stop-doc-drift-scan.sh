#!/usr/bin/env bash
# stop-doc-drift-scan.sh — Run DOC DRIFT check at session end.
#
# Finds files with stale 'kr-forensic-finance' references (excluding
# historical rename notes in "Previously known as" lines).
# Output is printed once so the user sees it before the session closes.

# Source shared config for BASE, HUB, and ALL_REPOS (single source of truth)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../../ecosystem.conf" 2>/dev/null || {
    # Fallback if sourcing fails
    BASE="/c/Users/pon00/Projects"
    HUB="$BASE/forensic-accounting-toolkit"
    ALL_REPOS=(forensic-accounting-toolkit kr-company-registry kr-trading-calendar
        kr-beneish kr-derivatives jfia-catalog jfia-forensic kr-enforcement-cases
        kr-forensic-core krff-shell kr-dart-pipeline kr-anomaly-scoring kr-stat-tests
        kr-real-estate)
}

# Build scan targets from ALL_REPOS (declared before the while loop)
SCAN_TARGETS=()
for r in "${ALL_REPOS[@]}"; do
    [ -f "$BASE/$r/CLAUDE.md" ] && SCAN_TARGETS+=("$BASE/$r/CLAUDE.md")
    [ -f "$BASE/$r/README.md" ] && SCAN_TARGETS+=("$BASE/$r/README.md")
done
SCAN_TARGETS+=(
    "$HUB/ARCHITECTURE.md" "$HUB/ECOSYSTEM.md"
    "$HUB/WORKFLOW.md" "$HUB/lessons.md" "$HUB"/*.conf
)

stale_files=()
while IFS= read -r f; do
    # Count lines that have stale name but are NOT historical/meta references
    real_stale=$(grep "kr-forensic-finance" "$f" 2>/dev/null \
        | grep -vc "Previously known as\|^\`kr-forensic-finance\`\|\"kr-forensic-finance\"")
    if [ "$real_stale" -gt 0 ]; then
        stale_files+=("${f#$BASE/}")
    fi
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
