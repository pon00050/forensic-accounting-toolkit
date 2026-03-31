#!/usr/bin/env bash
# scripts/ci/checkout-ecosystem.sh
# Reusable script: print symlink commands for ecosystem repos checked out via _deps/.
#
# All ecosystem repos are checked out to $GITHUB_WORKSPACE/_deps/<repo> by the
# workflow's actions/checkout steps. This script creates symlinks from the
# parent directory so that relative paths like ../kr-beneish work exactly as
# they do locally.
#
# Usage in workflow step:
#   - name: Symlink ecosystem repos
#     run: bash scripts/ci/checkout-ecosystem.sh
#
# The symlink pattern is proven in krff-shell/.github/workflows/test.yml.

set -euo pipefail

PARENT="$(dirname "$GITHUB_WORKSPACE")"

# All repos that may have been checked out to _deps/
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

for repo in "${REPOS[@]}"; do
    src="$GITHUB_WORKSPACE/_deps/$repo"
    dst="$PARENT/$repo"
    if [ -d "$src" ] && [ ! -e "$dst" ]; then
        ln -s "$src" "$dst"
        echo "  linked: $repo"
    fi
done

echo "Symlinks complete. Parent: $PARENT"
ls "$PARENT"
