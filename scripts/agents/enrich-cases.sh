#!/usr/bin/env bash
# scripts/agents/enrich-cases.sh
# Headless agent: enriches FSS/SFC enforcement cases with DART matches and Claude analysis.
#
# Usage:
#   bash scripts/agents/enrich-cases.sh
#
# Requires: ANTHROPIC_API_KEY and DART_API_KEY in environment or .env
# Output: JSON summary to stdout

set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CASES_DIR="$(cd "$HUB_DIR/../kr-enforcement-cases" 2>/dev/null && pwd)" || {
    echo "ERROR: kr-enforcement-cases not found at $HUB_DIR/../kr-enforcement-cases" >&2
    exit 1
}

exec claude -p "You are an enforcement case enrichment agent for the Korean forensic finance ecosystem.

Working directory: $CASES_DIR

Steps:
1. Read $CASES_DIR/CLAUDE.md for conventions and pipeline instructions
2. Check current state:
   - Count rows in $CASES_DIR/reports/violations.csv (baseline)
   - Check $CASES_DIR/data/curated/dart_matches.csv row count (current matches)
   - List any unenriched raw files in $CASES_DIR/data/raw/
3. Run DART company matching (if new cases exist):
   - cd $CASES_DIR && uv run python -m kr_enforcement_cases.match_dart_companies
4. Run Beneish ratio computation for matched companies:
   - uv run python -m kr_enforcement_cases.compute_beneish
5. Validate outputs:
   - Compare violations.csv row count (should be >= baseline)
   - Compare dart_matches.csv row count (should be >= before)
   - Check beneish_ratios.csv exists and has data
6. Run tests to verify nothing broke:
   - uv run pytest tests/ -q
7. Report JSON summary:
   {
     'status': 'ok' or 'error',
     'violations_before': N,
     'violations_after': N,
     'dart_matches_before': N,
     'dart_matches_after': N,
     'new_matches': [...],
     'tests_passed': true/false,
     'errors': [...]
   }

Rules:
- Do NOT run scraping steps (scrape_fss_cases, scrape_sfc_source1) — those require manual review
- Do NOT push to git or create commits
- Do NOT spend money on Claude API calls if no new cases exist (check first)" \
    --allowedTools "Bash(uv run *),Bash(python *),Bash(cd *),Bash(ls *),Read,Glob,Grep" \
    --output-format json \
    --max-turns 30 \
    --cwd "$CASES_DIR"
