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
BASE="/c/Users/pon00/Projects"
HUB="$BASE/forensic-accounting-toolkit"
GH="/c/Program Files/GitHub CLI/gh.exe"

REPOS=(
    forensic-accounting-toolkit
    kr-forensic-finance
    kr-company-registry
    kr-trading-calendar
    kr-beneish
    kr-derivatives
    jfia-catalog
    jfia-forensic
    kr-real-estate
)

# Helper: get file modification epoch timestamp (Windows/Git Bash compatible)
file_epoch() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "0"
        return
    fi
    # Try GNU stat first, then date -r fallback
    stat -c '%Y' "$file" 2>/dev/null || date -r "$file" '+%s' 2>/dev/null || echo "0"
}

# Helper: days since epoch timestamp
days_since() {
    local epoch="$1"
    local now
    now=$(date '+%s')
    if [ "$epoch" -eq 0 ]; then
        echo "unknown"
        return
    fi
    echo $(( (now - epoch) / 86400 ))
}

echo "=== TRIAGE SCAN (mode: $MODE, $(date '+%Y-%m-%d %H:%M')) ==="
echo ""

# ─────────────────────────────────────────────
# SOURCE 1: Board state
# ─────────────────────────────────────────────
echo "--- BOARD ---"
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
echo ""

# ─────────────────────────────────────────────
# SOURCE 2: Git hygiene
# ─────────────────────────────────────────────
echo "--- GIT HYGIENE ---"
for repo in "${REPOS[@]}"; do
    dir="$BASE/$repo"
    if [ ! -d "$dir/.git" ]; then
        continue
    fi

    uncommitted=$(cd "$dir" && git status --porcelain 2>/dev/null | head -20)
    unpushed=$(cd "$dir" && git log --oneline @{upstream}..HEAD 2>/dev/null || true)
    last_commit=$(cd "$dir" && git log -1 --format='%cr' 2>/dev/null || echo "unknown")

    status="CLEAN"
    details=""
    if [ -n "$uncommitted" ]; then
        count=$(echo "$uncommitted" | wc -l | tr -d ' ')
        status="UNCOMMITTED"
        details="$count files"
    fi
    if [ -n "$unpushed" ]; then
        up_count=$(echo "$unpushed" | wc -l | tr -d ' ')
        if [ "$status" = "CLEAN" ]; then
            status="UNPUSHED"
            details="$up_count commits"
        else
            status="UNCOMMITTED+UNPUSHED"
            details="$details, $up_count unpushed"
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
    recent=$(cd "$dir" && git log --oneline -5 --format='%s' 2>/dev/null | sed 's/^/    ~ /')
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
    # Extract unchecked items with their priority section
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
    # Extract board Todo titles and check against ECOSYSTEM.md checked items
    while IFS= read -r title; do
        [ -z "$title" ] && continue
        # Search for matching checked items in ECOSYSTEM.md (case-insensitive partial match)
        # Normalize: strip leading/trailing whitespace
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
        # Extract Status line
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
for repo in "${REPOS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir" ] || continue

    # Search Python files only, exclude common noise directories
    count=$(find "$dir" -type f -name '*.py' \
        ! -path '*/.venv/*' \
        ! -path '*/__pycache__/*' \
        ! -path '*/.eggs/*' \
        ! -path '*/build/*' \
        ! -path '*/node_modules/*' \
        ! -path '*/.git/*' \
        -exec grep -l 'TODO\|FIXME\|HACK\|NotImplementedError' {} \; 2>/dev/null | wc -l | tr -d ' ')

    if [ "$count" -gt 0 ]; then
        echo "  $repo: $count files with TODO/FIXME/HACK/NotImplementedError"
        # Show up to 5 specific signals
        find "$dir" -type f -name '*.py' \
            ! -path '*/.venv/*' \
            ! -path '*/__pycache__/*' \
            ! -path '*/.eggs/*' \
            ! -path '*/build/*' \
            ! -path '*/node_modules/*' \
            ! -path '*/.git/*' \
            -exec grep -Hn 'TODO\|FIXME\|HACK\|NotImplementedError' {} \; 2>/dev/null | head -5 | while read -r line; do
            # Strip the base path for readability
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
SRC_DIR="$BASE/kr-forensic-finance/01_Data/processed"
DST_DIR="$BASE/kr-derivatives/data/input"

parquets=(price_volume.parquet cb_bw_events.parquet corp_actions.parquet)

for pq in "${parquets[@]}"; do
    src_file="$SRC_DIR/$pq"
    dst_file="$DST_DIR/$pq"

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
    last_date=$(grep -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' "$changelog" 2>/dev/null | head -1 | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}')
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
for repo in "${REPOS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir" ] || continue

    issues=""
    # Check 1: CLAUDE.md exists
    if [ ! -f "$dir/CLAUDE.md" ]; then
        issues="${issues}CLAUDE.md "
    fi
    # Check 2: .claude/ directory exists (exception: jfia-catalog)
    if [ "$repo" != "jfia-catalog" ] && [ ! -d "$dir/.claude" ]; then
        issues="${issues}.claude/ "
    fi
    # Check 3: uv.lock tracked (if pyproject.toml exists, exception: jfia-catalog)
    if [ "$repo" != "jfia-catalog" ] && [ -f "$dir/pyproject.toml" ]; then
        if ! (cd "$dir" && git ls-files --error-unmatch uv.lock >/dev/null 2>&1); then
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
# TEST COUNTS: compare actual test counts to CLAUDE.md claims
# ─────────────────────────────────────────────
echo "--- TEST COUNTS ---"
declare -A CLAUDE_COUNTS=(
    [kr-company-registry]=18
    [kr-trading-calendar]=10
    [kr-beneish]=61
    [kr-derivatives]=79
    [jfia-forensic]=76
    [kr-forensic-finance]=306
)
test_drift=0
for repo in "${!CLAUDE_COUNTS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir" ] || continue
    claimed=${CLAUDE_COUNTS[$repo]}

    # Use the right test command per repo; parse "N tests" from last line
    if [ "$repo" = "kr-forensic-finance" ]; then
        actual=$(cd "$dir" && python -m pytest tests/ --co -q 2>/dev/null | tail -1 | sed 's/[^0-9]*//' | grep -oE '^[0-9]+' || echo "?")
    else
        actual=$(cd "$dir" && uv run pytest tests/ --co -q 2>/dev/null | tail -1 | sed 's/[^0-9]*//' | grep -oE '^[0-9]+' || echo "?")
    fi

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
for repo in "${REPOS[@]}"; do
    dir="$BASE/$repo"
    [ -d "$dir/.git" ] || continue

    branch_count=$(cd "$dir" && git branch --list 2>/dev/null | wc -l | tr -d ' ')
    if [ "$branch_count" -gt 3 ]; then
        branches=$(cd "$dir" && git branch --list 2>/dev/null | sed 's/^/    /')
        echo "  [WARN] $repo — $branch_count branches"
        echo "$branches"
    fi
done
echo "  (flagged if >3 branches)"
echo ""

# ─────────────────────────────────────────────
# SOURCE 10: Dependency chain checks
# ─────────────────────────────────────────────
echo "--- DEPENDENCY CHAIN ---"

# Check: kr-derivatives data/input/ exists and has parquets
if [ -d "$DST_DIR" ]; then
    pq_count=$(find "$DST_DIR" -name '*.parquet' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$pq_count" -eq 0 ]; then
        echo "  [BLOCKED] kr-derivatives has no input parquets — run: bash ecosystem.sh copy-parquets"
    else
        echo "  [OK] kr-derivatives has $pq_count input parquets"
    fi
else
    echo "  [BLOCKED] kr-derivatives/data/input/ missing"
fi

# Check: pyproject.toml uses hatchling (spot check repos that should)
for repo in kr-beneish kr-derivatives kr-trading-calendar jfia-forensic; do
    pptoml="$BASE/$repo/pyproject.toml"
    if [ -f "$pptoml" ]; then
        if ! grep -q 'hatchling' "$pptoml" 2>/dev/null; then
            echo "  [DRIFT] $repo — pyproject.toml does not use hatchling"
        fi
    fi
done

# Check: kr-forensic-finance has its pipeline outputs
if [ -d "$SRC_DIR" ]; then
    for pq in price_volume.parquet cb_bw_events.parquet; do
        if [ ! -f "$SRC_DIR/$pq" ]; then
            echo "  [WARN] kr-forensic-finance missing $pq in processed output"
        fi
    done
fi

echo ""
echo "--- END (full scan) ---"
