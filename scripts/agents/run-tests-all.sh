#!/usr/bin/env bash
# scripts/agents/run-tests-all.sh
# Headless agent: runs tests across all ecosystem repos and reports pass/fail.
#
# Usage:
#   bash scripts/agents/run-tests-all.sh
#
# No API keys required — all offline. Budget: $1 max.
# Output: pass/fail summary per repo.

set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$HUB_DIR"
exec claude --dangerously-skip-permissions -p "You are a test runner agent for the Korean forensic finance ecosystem.

Hub directory: $HUB_DIR

Run 'uv run pytest tests/ -v' in each of the following repos (sibling directories):
- $HUB_DIR/../kr-beneish
- $HUB_DIR/../kr-trading-calendar
- $HUB_DIR/../kr-derivatives
- $HUB_DIR/../jfia-forensic
- $HUB_DIR/../kr-enforcement-cases
- $HUB_DIR/../kr-company-registry

For each repo:
1. cd into the repo directory
2. Run: uv run pytest tests/ -v
3. Record: repo name, pass count, fail count, skip count, any error messages

Report a summary table:
| Repo | Tests | Passed | Failed | Skipped | Status |
|------|-------|--------|--------|---------|--------|
...

If any repo has failures, include the full error output for those tests.
If a repo directory does not exist, mark it as MISSING.

Do NOT modify any files. Do NOT push to git." \
    --max-budget-usd 1.00
