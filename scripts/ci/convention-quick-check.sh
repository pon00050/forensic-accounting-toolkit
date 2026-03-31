#!/usr/bin/env bash
# scripts/ci/convention-quick-check.sh
# Quick bash-only convention checks across all repos.
# Checks 5 high-signal conventions (no LLM needed).
#
# Outputs JSON to _scratchpad/convention-quick.json

set -euo pipefail

PARENT="$(dirname "$GITHUB_WORKSPACE")"
SCRATCHPAD="$GITHUB_WORKSPACE/_scratchpad"
mkdir -p "$SCRATCHPAD"

REPOS=(
    kr-company-registry
    kr-trading-calendar
    kr-beneish
    kr-derivatives
    jfia-catalog
    jfia-forensic
    kr-enforcement-cases
    kr-forensic-core
    krff-shell
    kr-dart-pipeline
    kr-anomaly-scoring
    kr-stat-tests
    kr-real-estate
)

# Repos exempt from specific checks
JFIA_CATALOG_EXEMPT="jfia-catalog"

DRIFT_COUNT=0
MISS_COUNT=0
declare -a DEVIATIONS=()

check() {
    local repo="$1" convention="$2" status="$3" detail="$4"
    if [ "$status" = "DRIFT" ] || [ "$status" = "MISS" ]; then
        DEVIATIONS+=("{\"repo\":\"$repo\",\"convention\":\"$convention\",\"status\":\"$status\",\"detail\":$(python3 -c "import json,sys; print(json.dumps('$detail'))")}")
        if [ "$status" = "DRIFT" ]; then ((DRIFT_COUNT++)); else ((MISS_COUNT++)); fi
    fi
}

for repo in "${REPOS[@]}"; do
    rpath="$PARENT/$repo"
    [ -d "$rpath" ] || continue

    pyproject="$rpath/pyproject.toml"

    # Convention 1: Build system (hatchling)
    if [ "$repo" = "$JFIA_CATALOG_EXEMPT" ]; then
        : # exempt
    elif [ -f "$pyproject" ]; then
        if ! grep -q "hatchling" "$pyproject" 2>/dev/null; then
            check "$repo" "build-system" "DRIFT" "hatchling not found in pyproject.toml"
        fi
    else
        check "$repo" "build-system" "MISS" "pyproject.toml absent"
    fi

    # Convention 5: uv.lock committed
    if [ "$repo" = "$JFIA_CATALOG_EXEMPT" ]; then
        : # exempt
    else
        repo_dir="$rpath"
        if [ -d "$repo_dir/.git" ] || git -C "$repo_dir" rev-parse --git-dir &>/dev/null 2>&1; then
            if ! git -C "$repo_dir" ls-files --error-unmatch uv.lock &>/dev/null 2>&1; then
                check "$repo" "uv.lock" "MISS" "uv.lock not committed to git"
            fi
        fi
    fi

    # Convention 10: .claude/ directory
    if [ "$repo" = "$JFIA_CATALOG_EXEMPT" ]; then
        : # exempt
    elif [ ! -d "$rpath/.claude" ]; then
        check "$repo" ".claude-dir" "MISS" ".claude/ directory absent"
    fi

    # Convention 11: compile-bytecode
    if [ -f "$pyproject" ]; then
        if ! grep -q "compile-bytecode" "$pyproject" 2>/dev/null; then
            check "$repo" "compile-bytecode" "MISS" "compile-bytecode = false missing from [tool.uv]"
        fi
    fi

    # Convention 12: CLAUDE.md
    if [ ! -f "$rpath/CLAUDE.md" ]; then
        check "$repo" "CLAUDE.md" "MISS" "CLAUDE.md absent"
    fi

done

TOTAL=$((DRIFT_COUNT + MISS_COUNT))
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "$TOTAL" -eq 0 ]; then
    DEVIATIONS_JSON="[]"
else
    DEVIATIONS_JSON="[$(IFS=,; echo "${DEVIATIONS[*]}")]"
fi

cat > "$SCRATCHPAD/convention-quick.json" <<EOF
{
  "generated_at": "$TIMESTAMP",
  "drift_count": $DRIFT_COUNT,
  "miss_count": $MISS_COUNT,
  "total_deviations": $TOTAL,
  "deviations": $DEVIATIONS_JSON
}
EOF

echo "convention quick-check: $DRIFT_COUNT DRIFT, $MISS_COUNT MISS (total: $TOTAL deviations)"
