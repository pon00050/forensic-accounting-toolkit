#!/usr/bin/env bash
# ecosystem.sh — Cross-repo operations for the forensic accounting ecosystem
# Run from the forensic-accounting-toolkit directory (the hub).
#
# Usage:
#   bash ecosystem.sh test-all          Run tests in all repos (sequential)
#   bash ecosystem.sh test <repo>       Run tests in one repo
#   bash ecosystem.sh status            Git status across all repos
#   bash ecosystem.sh copy-parquets     Copy pipeline outputs to downstream inputs
#   bash ecosystem.sh unpushed          Show repos with unpushed commits

set -euo pipefail

# Source shared config (paths, repo list, test commands)
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ecosystem.conf"

cmd_test_all() {
    echo "=== Testing all repos ==="
    local failed=()
    for repo in "${REPOS_WITH_TESTS[@]}"; do
        local dir="$BASE/$repo"
        if [ ! -d "$dir" ]; then
            echo "  [SKIP] $repo — directory not found"
            continue
        fi
        if [ ! -d "$dir/tests" ]; then
            echo "  [SKIP] $repo — no tests/ directory"
            continue
        fi
        echo ""
        echo "--- $repo ---"
        local cmd
        cmd=$(test_cmd "$repo")
        if (cd "$dir" && eval "$cmd"); then
            echo "  [PASS] $repo"
        else
            echo "  [FAIL] $repo"
            failed+=("$repo")
        fi
    done
    echo ""
    echo "=== Summary ==="
    if [ ${#failed[@]} -eq 0 ]; then
        echo "All repos passed."
    else
        echo "FAILED: ${failed[*]}"
        return 1
    fi
}

cmd_test() {
    local repo="${1:?Usage: ecosystem.sh test <repo-name>}"
    local dir="$BASE/$repo"
    if [ ! -d "$dir" ]; then
        echo "Error: $dir not found"
        return 1
    fi
    local cmd
    cmd=$(test_cmd "$repo")
    echo "--- $repo ---"
    (cd "$dir" && eval "$cmd")
}

cmd_status() {
    echo "=== Git status across ecosystem ==="
    for repo in "${ALL_REPOS[@]}"; do
        local dir="$BASE/$repo"
        [ -d "$dir/.git" ] || continue
        local status
        status=$(git -C "$dir" status --short 2>/dev/null)
        local unpushed
        unpushed=$(git -C "$dir" log --oneline @{upstream}..HEAD 2>/dev/null || true)
        if [ -z "$status" ] && [ -z "$unpushed" ]; then
            echo "  [OK] $repo"
        else
            if [ -n "$status" ]; then
                echo "  [!!] $repo — uncommitted changes:"
                echo "$status" | sed 's/^/       /'
            fi
            if [ -n "$unpushed" ]; then
                echo "  [>>] $repo — unpushed commits:"
                echo "$unpushed" | sed 's/^/       /'
            fi
        fi
    done
}

cmd_copy_parquets() {
    echo "=== Copying pipeline outputs to downstream inputs ==="

    for f in "${PARQUET_FILES[@]}"; do
        if cp "$PIPELINE_SRC/$f" "$PIPELINE_DST/$f" 2>/dev/null; then
            echo "  [OK] $f → kr-derivatives/data/input/"
        else
            echo "  [--] $f — not found in krff-shell output"
        fi
    done
}

cmd_unpushed() {
    echo "=== Repos with unpushed commits ==="
    local found=0
    for repo in "${ALL_REPOS[@]}"; do
        local dir="$BASE/$repo"
        [ -d "$dir/.git" ] || continue
        local unpushed
        unpushed=$(git -C "$dir" log --oneline @{upstream}..HEAD 2>/dev/null || true)
        if [ -n "$unpushed" ]; then
            echo "  $repo:"
            echo "$unpushed" | sed 's/^/    /'
            found=1
        fi
    done
    if [ "$found" -eq 0 ]; then
        echo "  All repos pushed."
    fi
}

# Dispatch
case "${1:-help}" in
    test-all)       cmd_test_all ;;
    test)           cmd_test "${2:-}" ;;
    status)         cmd_status ;;
    copy-parquets)  cmd_copy_parquets ;;
    unpushed)       cmd_unpushed ;;
    help|*)
        echo "Usage: bash ecosystem.sh <command>"
        echo ""
        echo "Commands:"
        echo "  test-all        Run tests in all repos"
        echo "  test <repo>     Run tests in one repo"
        echo "  status          Git status across all repos"
        echo "  copy-parquets   Copy pipeline outputs to downstream inputs"
        echo "  unpushed        Show repos with unpushed commits"
        ;;
esac
