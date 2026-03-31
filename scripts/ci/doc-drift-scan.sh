#!/usr/bin/env bash
# scripts/ci/doc-drift-scan.sh
# Scan all repos for stale "kr-forensic-finance" references.
# Excludes: files under reports/ (historical session logs), backtick code spans.
#
# Outputs JSON to _scratchpad/doc-drift.json
# Exits 0 always (findings reported via JSON + GitHub issue creation in workflow).

set -euo pipefail

PARENT="$(dirname "$GITHUB_WORKSPACE")"
SCRATCHPAD="$GITHUB_WORKSPACE/_scratchpad"
mkdir -p "$SCRATCHPAD"

REPOS=(
    forensic-accounting-toolkit
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

declare -a FINDINGS=()

for repo in "${REPOS[@]}"; do
    repo_path="$PARENT/$repo"
    [ -d "$repo_path" ] || continue

    # Search .md, .toml, .conf files; exclude:
    #   reports/       — historical session logs
    #   CHANGELOG.md   — audit trail, will always contain historical mentions
    #   skills/        — skill files contain the old name as grep detection patterns
    while IFS= read -r match; do
        # Skip files under reports/ (historical session logs)
        if echo "$match" | grep -q "/reports/"; then
            continue
        fi
        # Extract file path (before the colon-line pattern)
        filepath="${match%%:*}"
        linenum=$(echo "$match" | cut -d: -f2)
        linetext=$(echo "$match" | cut -d: -f3-)
        # Skip if the match is inside a backtick span (inline code reference)
        if echo "$linetext" | grep -qP '`[^`]*kr-forensic-finance[^`]*`'; then
            continue
        fi
        # Skip if the match is inside double quotes (grep pattern or documentation string)
        if echo "$linetext" | grep -qP '"[^"]*kr-forensic-finance[^"]*"'; then
            continue
        fi
        # Skip lines explicitly about the old name (meta-references)
        if echo "$linetext" | grep -qi "previously known as\|renamed from\|old name"; then
            continue
        fi
        FINDINGS+=("{\"repo\":\"$repo\",\"file\":\"$filepath\",\"line\":$linenum,\"text\":$(echo "$linetext" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')}")
    done < <(grep -rn \
        --include="*.md" --include="*.toml" --include="*.conf" \
        --exclude="CHANGELOG.md" \
        --exclude-dir="skills" \
        --exclude-dir="reports" \
        "kr-forensic-finance" "$repo_path" 2>/dev/null || true)
done

COUNT=${#FINDINGS[@]}
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build JSON array
if [ "$COUNT" -eq 0 ]; then
    FINDINGS_JSON="[]"
else
    FINDINGS_JSON="[$(IFS=,; echo "${FINDINGS[*]}")]"
fi

cat > "$SCRATCHPAD/doc-drift.json" <<EOF
{
  "generated_at": "$TIMESTAMP",
  "stale_ref_count": $COUNT,
  "findings": $FINDINGS_JSON
}
EOF

echo "doc-drift scan: $COUNT stale references found"
if [ "$COUNT" -gt 0 ]; then
    echo "FILES WITH DRIFT:"
    for f in "${FINDINGS[@]}"; do
        echo "  $f"
    done
fi
