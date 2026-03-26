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

set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KRFF_DIR="$(cd "$HUB_DIR/../kr-forensic-finance" 2>/dev/null && pwd)" || {
    echo "ERROR: kr-forensic-finance not found at $HUB_DIR/../kr-forensic-finance" >&2
    exit 1
}

ARGS="${*:-}"

exec claude -p "You are a pipeline execution agent running from the forensic-accounting-toolkit hub.

Your working context:
- Hub: $HUB_DIR
- Pipeline repo: $KRFF_DIR
- Extra args: $ARGS

Steps to execute:
1. Read $KRFF_DIR/CLAUDE.md to understand current conventions and test command
2. Check data freshness: list modification times of all .parquet files in $KRFF_DIR/01_Data/processed/
3. Run the pipeline (cd to $KRFF_DIR first):
   - uv run krff run --stage dart $ARGS
   - uv run krff run --stage cb_bw $ARGS
4. Run analysis:
   - uv run python 03_Analysis/beneish_screen.py (or equivalent command from CLAUDE.md)
5. Sync downstream: cd back to $HUB_DIR && bash ecosystem.sh copy-parquets
6. Validate outputs:
   - For each .parquet in $KRFF_DIR/01_Data/processed/, check: file exists, size > 0, row count > 0
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
- Use 'uv run' for all Python commands in $KRFF_DIR" \
    --allowedTools "Bash(uv run *),Bash(python *),Bash(bash ecosystem.sh *),Bash(bash $HUB_DIR/ecosystem.sh *),Bash(cd *),Bash(ls *),Read,Glob,Grep" \
    --output-format json \
    --max-turns 40 \
    --cwd "$HUB_DIR"
