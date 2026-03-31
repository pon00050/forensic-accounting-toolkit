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

# Repos are symlinked to $GITHUB_WORKSPACE/<repo> by checkout-ecosystem.sh
# ($PARENT/<repo> does not exist — clones are at $GITHUB_WORKSPACE/_deps/<repo>)
REPO_BASE="$GITHUB_WORKSPACE"

declare -A COLLECTION_FAILED=()

# Collect actual counts
for repo in "${!TEST_RUNNERS[@]}"; do
    rpath="$REPO_BASE/$repo"
    if [ ! -d "$rpath" ]; then
        COLLECTION_FAILED[$repo]=1
        ACTUAL_COUNTS[$repo]=0
        continue
    fi
    runner="${TEST_RUNNERS[$repo]}"
    cd "$rpath"
    # Collect test count; capture exit code to distinguish failure from genuine 0
    count_line=$(eval "$runner tests/ --co -q 2>/dev/null | tail -2 | head -1")
    exit_code=$?
    actual=$(echo "$count_line" | grep -oP '^\d+' || echo "0")
    if [ "$exit_code" -ne 0 ] || [ "$actual" = "0" ]; then
        # Treat as collection failure, not a genuine zero-test count
        COLLECTION_FAILED[$repo]=1
        actual=0
    fi
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

# Compare — skip repos where collection failed (actual=0 means env broken, not no tests)
for repo in "${!ACTUAL_COUNTS[@]}"; do
    if [ -n "${COLLECTION_FAILED[$repo]:-}" ]; then
        continue  # collection failure — not a real mismatch, suppress from issue
    fi
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
