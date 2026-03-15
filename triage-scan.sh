#!/usr/bin/env bash
# triage-scan.sh — Collect task signals from 10 sources across the ecosystem
#
# Usage:
#   bash triage-scan.sh           Full scan (all 10 sources, ~8s)
#   bash triage-scan.sh quick     Quick scan (sources 1-3 only, ~4s)
#
# Output: Structured sections (--- SOURCE NAME ---) for skill parsing.
# Designed to continue on individual failures (no set -e).

set -uo pipefail

MODE="${1:-full}"

# Source shared config (paths, repo list, GH CLI, test commands)
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ecosystem.conf"

# Helper: get file modification epoch timestamp (Windows/Git Bash compatible)
file_epoch() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "0"
        return
    fi
    stat -c '%Y' "$file" 2>/dev/null || date -r "$file" '+%s' 2>/dev/null || echo "0"
}

echo "=== TRIAGE SCAN (mode: $MODE, $(date '+%Y-%m-%d %H:%M')) ==="
echo ""

# ─────────────────────────────────────────────
# SOURCE 1: Board state
# ─────────────────────────────────────────────
echo "--- BOARD ---"
if [ -n "$GH" ]; then
    BOARD_JSON=$("$GH" project item-list 1 --owner pon00050 --format json 2>/dev/null) && {
        echo "$BOARD_JSON" | python -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('items', [])
by_status = {}
for i in items:
    s = i.get('status', 'Unknown')
    by_status.setdefault(s, []).append(i)
for status in ['Todo', 'In Progress', 'Done']:
    group = by_status.get(status, [])
    if group:
        print(f'{status}: {len(group)}')
        for i in group:
            title = i.get('title', '?')
            priority = i.get('priority', '?')
            owner = i.get('owner', '?')
            print(f'  [{priority}] [{owner}] {title}')
" 2>/dev/null
    } || echo "UNAVAILABLE (gh CLI offline or auth issue)"
else
    echo "UNAVAILABLE (gh CLI not found)"
fi
echo ""

# ─────────────────────────────────────────────
# SOURCE 2: Git hygiene
# ─────────────────────────────────────────────
echo "--- GIT HYGIENE ---"
for repo in "${ALL_REPOS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir/.git" ] || continue

    uncommitted=$(git -C "$dir" status --porcelain 2>/dev/null | head -20)
    unpushed=$(git -C "$dir" log --oneline @{upstream}..HEAD 2>/dev/null || true)
    last_commit=$(git -C "$dir" log -1 --format='%cr' 2>/dev/null || echo "unknown")

    status="CLEAN"
    if [ -n "$uncommitted" ]; then
        count=$(echo "$uncommitted" | wc -l | tr -d ' ')
        status="UNCOMMITTED"
    fi
    if [ -n "$unpushed" ]; then
        if [ "$status" = "CLEAN" ]; then
            status="UNPUSHED"
        else
            status="UNCOMMITTED+UNPUSHED"
        fi
    fi

    echo "  [$status] $repo (last commit: $last_commit)"
    if [ -n "$uncommitted" ]; then
        echo "$uncommitted" | sed 's/^/    /'
    fi
    if [ -n "$unpushed" ]; then
        echo "$unpushed" | sed 's/^/    >> /'
    fi
    # Recent commit subjects — enables LLM to cross-reference board claims vs actual work
    recent=$(git -C "$dir" log --oneline -5 --format='%s' 2>/dev/null | sed 's/^/    ~ /')
    if [ -n "$recent" ]; then
        echo "$recent"
    fi
done
echo ""

# ─────────────────────────────────────────────
# SOURCE 3: ECOSYSTEM.md backlog
# ─────────────────────────────────────────────
echo "--- BACKLOG ---"
if [ -f "$HUB/ECOSYSTEM.md" ]; then
    current_priority=""
    while IFS= read -r line; do
        if [[ "$line" =~ ^###[[:space:]]+(P[0-9]) ]]; then
            current_priority="${BASH_REMATCH[1]}"
        fi
        if [[ "$line" =~ ^-[[:space:]]\[[[:space:]]\] ]]; then
            echo "  [$current_priority] $line"
        fi
    done < "$HUB/ECOSYSTEM.md"
else
    echo "  ECOSYSTEM.md not found"
fi
echo ""

# ─────────────────────────────────────────────
# BOARD FRESHNESS: cross-check board Todo items against ECOSYSTEM.md completed items
# ─────────────────────────────────────────────
echo "--- BOARD FRESHNESS ---"
if [ -n "${BOARD_JSON:-}" ] && [ -f "$HUB/ECOSYSTEM.md" ]; then
    stale_count=0
    while IFS= read -r title; do
        [ -z "$title" ] && continue
        match=$(grep -i "\[x\].*$(echo "$title" | sed 's/[]\/$*.^[]/\\&/g' | cut -c1-30)" "$HUB/ECOSYSTEM.md" 2>/dev/null | head -1)
        if [ -n "$match" ]; then
            echo "  [STALE] \"$title\" — ECOSYSTEM.md shows completed"
            echo "    $match"
            stale_count=$((stale_count + 1))
        fi
    done < <(echo "$BOARD_JSON" | python -c "
import sys, json
data = json.load(sys.stdin)
for i in data.get('items', []):
    if i.get('status') == 'Todo':
        print(i.get('title', ''))
" 2>/dev/null)
    if [ "$stale_count" -eq 0 ]; then
        echo "  [OK] All board Todo items appear current"
    else
        echo "  $stale_count stale item(s) found — consider marking Done on the board"
    fi
else
    echo "  [SKIP] Board data or ECOSYSTEM.md unavailable"
fi
echo ""

# ─────────────────────────────────────────────
# Quick mode stops here
# ─────────────────────────────────────────────
if [ "$MODE" = "quick" ]; then
    echo "--- END (quick mode — run /triage for full scan) ---"
    exit 0
fi

# ─────────────────────────────────────────────
# SOURCE 4: Cross-issue status
# ─────────────────────────────────────────────
echo "--- CROSS-ISSUES ---"
if [ -d "$HUB/cross-issues" ]; then
    for f in "$HUB"/cross-issues/*.md; do
        [ -f "$f" ] || continue
        basename=$(basename "$f" .md)
        status_line=$(grep -m1 '^\*\*Status\*\*' "$f" 2>/dev/null || echo "Status: unknown")
        echo "  $basename: $status_line"
    done
else
    echo "  No cross-issues directory"
fi
echo ""

# ─────────────────────────────────────────────
# SOURCE 5: Code signals (TODO/FIXME/HACK/NotImplementedError)
# ─────────────────────────────────────────────
echo "--- CODE SIGNALS ---"
total_signals=0
for repo in "${ALL_REPOS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir" ] || continue

    # Single find pass: collect matches, count and display from same result
    matches=$(find "$dir" -type f -name '*.py' \
        ! -path '*/.venv/*' \
        ! -path '*/__pycache__/*' \
        ! -path '*/.eggs/*' \
        ! -path '*/build/*' \
        ! -path '*/node_modules/*' \
        ! -path '*/.git/*' \
        -exec grep -Hn 'TODO\|FIXME\|HACK\|NotImplementedError' {} \; 2>/dev/null)

    if [ -n "$matches" ]; then
        # Count unique files from grep -Hn output (file:line:match)
        count=$(echo "$matches" | cut -d: -f1 | sort -u | wc -l | tr -d ' ')
        echo "  $repo: $count files with TODO/FIXME/HACK/NotImplementedError"
        echo "$matches" | head -5 | while read -r line; do
            echo "    ${line#$BASE/}"
        done
        total_signals=$((total_signals + count))
    fi
done
if [ "$total_signals" -eq 0 ]; then
    echo "  No signals found"
fi
echo ""

# ─────────────────────────────────────────────
# SOURCE 6: Data freshness (parquet sync)
# ─────────────────────────────────────────────
echo "--- DATA FRESHNESS ---"
for pq in "${PARQUET_FILES[@]}"; do
    src_file="$PIPELINE_SRC/$pq"
    dst_file="$PIPELINE_DST/$pq"

    if [ ! -f "$src_file" ]; then
        echo "  [MISSING] $pq — not in kr-forensic-finance output"
        continue
    fi
    if [ ! -f "$dst_file" ]; then
        echo "  [MISSING] $pq — not in kr-derivatives input"
        continue
    fi

    src_epoch=$(file_epoch "$src_file")
    dst_epoch=$(file_epoch "$dst_file")

    if [ "$src_epoch" -gt "$dst_epoch" ]; then
        echo "  [STALE] $pq — source newer than downstream copy"
        echo "    Source: $(date -d @"$src_epoch" '+%Y-%m-%d %H:%M' 2>/dev/null || date -r "$src_file" '+%Y-%m-%d %H:%M' 2>/dev/null || echo 'unknown')"
        echo "    Copy:   $(date -d @"$dst_epoch" '+%Y-%m-%d %H:%M' 2>/dev/null || date -r "$dst_file" '+%Y-%m-%d %H:%M' 2>/dev/null || echo 'unknown')"
    else
        echo "  [OK] $pq — in sync"
    fi
done
echo ""

# ─────────────────────────────────────────────
# SOURCE 7: CHANGELOG freshness
# ─────────────────────────────────────────────
echo "--- CHANGELOG FRESHNESS ---"
changelog="$HUB/CHANGELOG.md"
if [ -f "$changelog" ]; then
    last_date=$(grep -m1 -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' "$changelog" 2>/dev/null | sed 's/^## //')
    if [ -n "$last_date" ]; then
        echo "  Last CHANGELOG entry: $last_date"
        today=$(date '+%Y-%m-%d')
        if [ "$last_date" != "$today" ]; then
            echo "  [STALE] Not updated today ($today)"
        else
            echo "  [OK] Updated today"
        fi
    else
        echo "  [WARN] No dated section found in CHANGELOG.md"
    fi
else
    echo "  [MISSING] CHANGELOG.md not found"
fi
echo ""

# ─────────────────────────────────────────────
# SOURCE 8: Convention quick-check
# ─────────────────────────────────────────────
echo "--- CONVENTION QUICK-CHECK ---"
conv_drift=0
for repo in "${ALL_REPOS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir" ] || continue

    issues=""
    if [ ! -f "$dir/CLAUDE.md" ]; then
        issues="${issues}CLAUDE.md "
    fi
    if [ -f "$dir/pyproject.toml" ] && [ "$repo" != "jfia-catalog" ] && [ ! -d "$dir/.claude" ]; then
        issues="${issues}.claude/ "
    fi
    if [ "$repo" != "jfia-catalog" ] && [ -f "$dir/pyproject.toml" ]; then
        if ! git -C "$dir" ls-files --error-unmatch uv.lock >/dev/null 2>&1; then
            issues="${issues}uv.lock "
        fi
    fi

    if [ -n "$issues" ]; then
        echo "  [DRIFT] $repo — missing: $issues"
        conv_drift=1
    fi
done
if [ "$conv_drift" -eq 0 ]; then
    echo "  [OK] All repos pass quick convention check"
fi
echo ""

# ─────────────────────────────────────────────
# TEST COUNTS: compare actual test counts to CLAUDE.md claims (dynamically parsed)
# ─────────────────────────────────────────────
echo "--- TEST COUNTS ---"
declare -A CLAUDE_COUNTS=()
eval "$(parse_claude_test_counts)"

test_drift=0
for repo in "${REPOS_WITH_TESTS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir" ] || continue

    claimed="${CLAUDE_COUNTS[$repo]:-}"
    if [ -z "$claimed" ]; then
        continue
    fi

    collect_cmd=$(test_collect_cmd "$repo")
    actual=$(cd "$dir" && eval "$collect_cmd" 2>/dev/null | tail -1 | sed 's/[^0-9]*//' | grep -oE '^[0-9]+' || echo "?")

    if [ "$actual" = "?" ]; then
        echo "  [WARN] $repo — could not collect tests"
    elif [ "$actual" -eq "$claimed" ]; then
        echo "  [OK] $repo — $actual tests (matches CLAUDE.md)"
    else
        echo "  [STALE] $repo — CLAUDE.md says $claimed, actual is $actual"
        test_drift=1
    fi
done
if [ "$test_drift" -eq 0 ]; then
    echo "  All test counts match CLAUDE.md"
fi
echo ""

# ─────────────────────────────────────────────
# SOURCE 9: Stale branches
# ─────────────────────────────────────────────
echo "--- STALE BRANCHES ---"
for repo in "${ALL_REPOS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir/.git" ] || continue

    branches=$(git -C "$dir" branch --list 2>/dev/null)
    branch_count=$(echo "$branches" | wc -l | tr -d ' ')
    if [ "$branch_count" -gt 3 ]; then
        echo "  [WARN] $repo — $branch_count branches"
        echo "$branches" | sed 's/^/    /'
    fi
done
echo "  (flagged if >3 branches)"
echo ""

# ─────────────────────────────────────────────
# SOURCE 10: Dependency chain checks
# ─────────────────────────────────────────────
echo "--- DEPENDENCY CHAIN ---"

# Check: kr-derivatives data/input/ exists and has parquets
if [ -d "$PIPELINE_DST" ]; then
    pq_count=$(find "$PIPELINE_DST" -name '*.parquet' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$pq_count" -eq 0 ]; then
        echo "  [BLOCKED] kr-derivatives has no input parquets — run: bash ecosystem.sh copy-parquets"
    else
        echo "  [OK] kr-derivatives has $pq_count input parquets"
    fi
else
    echo "  [BLOCKED] kr-derivatives/data/input/ missing"
fi

# Check: pyproject.toml uses hatchling (all repos with pyproject.toml, except jfia-catalog)
for repo in "${ALL_REPOS[@]}"; do
    pptoml="$BASE/$repo/pyproject.toml"
    if [ "$repo" != "jfia-catalog" ] && [ "$repo" != "forensic-accounting-toolkit" ] && [ -f "$pptoml" ]; then
        if ! grep -q 'hatchling' "$pptoml" 2>/dev/null; then
            echo "  [DRIFT] $repo — pyproject.toml does not use hatchling"
        fi
    fi
done

# Check: kr-forensic-finance has its pipeline outputs (uses shared PARQUET_FILES)
if [ -d "$PIPELINE_SRC" ]; then
    for pq in "${PARQUET_FILES[@]}"; do
        if [ ! -f "$PIPELINE_SRC/$pq" ]; then
            echo "  [WARN] kr-forensic-finance missing $pq in processed output"
        fi
    done
fi

echo ""
echo "--- END (full scan) ---"
