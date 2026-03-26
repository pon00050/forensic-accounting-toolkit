#!/usr/bin/env bash
# scripts/agents/run-pipeline.sh
# Headless agent: runs the full kr-forensic-finance ETL pipeline with validation.
#
# Usage:
#   bash scripts/agents/run-pipeline.sh              # full run
#   bash scripts/agents/run-pipeline.sh --sample 20  # sample mode (fast)
#   bash scripts/agents/run-pipeline.sh --stage dart # single stage
#
# The agent will: extract → transform → analyze → copy-parquets → validate → report.
# Output: JSON summary to stdout, errors to stderr.
#
# Requires: DART_API_KEY, ANTHROPIC_API_KEY in environment or .env

set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KRFF_DIR="$(cd "$HUB_DIR/../kr-forensic-finance" 2>/dev/null && pwd)" || {
    echo "ERROR: kr-forensic-finance not found at $HUB_DIR/../kr-forensic-finance" >&2
    exit 1
}

ARGS="${*:-}"

cd "$KRFF_DIR"
exec claude --dangerously-skip-permissions -p "You are a pipeline execution agent running in the kr-forensic-finance repo.

Your working context:
- Current directory: $KRFF_DIR
- Hub: $HUB_DIR
- Extra args: $ARGS

Steps to execute:
1. Read CLAUDE.md to understand current conventions and test command
2. Check data freshness: list modification times of all .parquet files in 01_Data/processed/
3. Run the pipeline:
   - uv run python cli.py run --stage dart $ARGS
   - uv run python cli.py run --stage cb_bw $ARGS
4. Run analysis (check CLAUDE.md for exact command):
   - uv run python 03_Analysis/beneish_screen.py (or equivalent)
5. Sync downstream: cd $HUB_DIR && bash ecosystem.sh copy-parquets && cd $KRFF_DIR
6. Validate outputs:
   - For each .parquet in 01_Data/processed/, check: file exists, size > 0, row count > 0
   - python -c \"import pandas as pd; df=pd.read_parquet('<file>'); print(len(df), 'rows')\"
7. Report a JSON summary:
   {
     'status': 'ok' or 'error',
     'stages_completed': [...],
     'parquet_counts': {'filename': rowcount, ...},
     'errors': [...],
     'duration_seconds': N
   }

Rules:
- If any stage fails, continue to validation but include the error in the report
- Do NOT push to git
- Do NOT modify source files
- Use 'uv run' for all Python commands" \
    --max-budget-usd 5.00
