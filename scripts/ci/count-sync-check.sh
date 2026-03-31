#!/usr/bin/env bash
# scripts/ci/count-sync-check.sh
# Compare actual pytest test counts vs claimed counts in hub CLAUDE.md.
# Outputs JSON to _scratchpad/count-sync.json

set -euo pipefail

PARENT="$(dirname "$GITHUB_WORKSPACE")"
SCRATCHPAD="$GITHUB_WORKSPACE/_scratchpad"
mkdir -p "$SCRATCHPAD"

HUB="$GITHUB_WORKSPACE"

# Repos with test suites and their test runner
declare -A TEST_RUNNERS=(
    [kr-company-registry]="pytest"
    [kr-trading-calendar]="uv run pytest"
    [kr-beneish]="uv run pytest"
    [kr-derivatives]="uv run pytest"
    [jfia-forensic]="uv run pytest"
    [kr-enforcement-cases]="uv run pytest"
    [kr-forensic-core]="uv run pytest"
    [krff-shell]="uv run pytest"
    [kr-dart-pipeline]="uv run pytest"
    [kr-anomaly-scoring]="uv run pytest"
    [kr-stat-tests]="uv run pytest"
)

declare -A ACTUAL_COUNTS=()
declare -A CLAIMED_COUNTS=()
declare -a MISMATCHES=()

# Collect actual counts
for repo in "${!TEST_RUNNERS[@]}"; do
    rpath="$PARENT/$repo"
    [ -d "$rpath" ] || continue
    runner="${TEST_RUNNERS[$repo]}"
    cd "$rpath"
    # Collect test count (--co -q shows "X tests collected")
    count_line=$(eval "$runner tests/ --co -q 2>/dev/null | tail -2 | head -1" || echo "0 tests")
    actual=$(echo "$count_line" | grep -oP '^\d+' || echo "0")
    ACTUAL_COUNTS[$repo]="$actual"
    cd "$GITHUB_WORKSPACE"
done

# Parse claimed counts from hub CLAUDE.md
# Matches lines like: | **kr-beneish** | ... | 61 |
while IFS= read -r line; do
    if [[ "$line" =~ \|\s*\*\*([^\*]+)\*\*\s*\|.*\|\s*([0-9]+)\s*\| ]]; then
        repo="${BASH_REMATCH[1]}"
        count="${BASH_REMATCH[2]}"
        CLAIMED_COUNTS[$repo]="$count"
    fi
done < "$HUB/CLAUDE.md"

# Compare
for repo in "${!ACTUAL_COUNTS[@]}"; do
    actual="${ACTUAL_COUNTS[$repo]}"
    claimed="${CLAIMED_COUNTS[$repo]:-unknown}"
    if [ "$claimed" = "unknown" ] || [ "$actual" != "$claimed" ]; then
        MISMATCHES+=("{\"repo\":\"$repo\",\"actual\":$actual,\"claimed\":\"$claimed\"}")
    fi
done

MISMATCH_COUNT=${#MISMATCHES[@]}
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build actual counts JSON
ACTUAL_JSON="{"
first=1
for repo in "${!ACTUAL_COUNTS[@]}"; do
    [ $first -eq 0 ] && ACTUAL_JSON+=","
    ACTUAL_JSON+="\"$repo\":${ACTUAL_COUNTS[$repo]}"
    first=0
done
ACTUAL_JSON+="}"

if [ "$MISMATCH_COUNT" -eq 0 ]; then
    MISMATCHES_JSON="[]"
else
    MISMATCHES_JSON="[$(IFS=,; echo "${MISMATCHES[*]}")]"
fi

cat > "$SCRATCHPAD/count-sync.json" <<EOF
{
  "generated_at": "$TIMESTAMP",
  "mismatch_count": $MISMATCH_COUNT,
  "mismatches": $MISMATCHES_JSON,
  "actual_counts": $ACTUAL_JSON
}
EOF

echo "count-sync: $MISMATCH_COUNT mismatches between actual and CLAUDE.md claimed counts"
