#!/usr/bin/env bash
# scripts/agents/sync-repos.sh
# Headless agent: syncs data artifacts between ecosystem repos.
#
# Specifically copies parquets from kr-dart-pipeline/krff-shell output → kr-derivatives input,
# verifies the copy, and reports any schema drift between source and destination.
#
# Usage:
#   bash scripts/agents/sync-repos.sh
#
# Output: JSON summary to stdout

set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$HUB_DIR"
exec claude --dangerously-skip-permissions -p "You are a cross-repo sync agent for the Korean forensic finance ecosystem.

Current directory: $HUB_DIR

Steps:
1. Read ecosystem.conf to understand PIPELINE_SRC, PIPELINE_DST, and PARQUET_FILES
2. For each file in PARQUET_FILES, check:
   a. Source exists: PIPELINE_SRC/<file>
   b. Destination exists: PIPELINE_DST/<file>
   c. Whether source is newer than destination (needs copy)
3. Run sync if needed: bash ecosystem.sh copy-parquets
4. Verify the copy: compare row counts of source vs destination for each parquet
   - python -c \"import pandas as pd; s=pd.read_parquet('<src>'); d=pd.read_parquet('<dst>'); print('rows match' if len(s)==len(d) else f'MISMATCH: src={len(s)} dst={len(d)}')\"
5. Check kr-enforcement-cases dart_matches.csv freshness:
   - Read ../kr-enforcement-cases/data/curated/dart_matches.csv
   - Report row count and last modification date
6. Report JSON summary:
   {
     'status': 'ok' or 'warning',
     'files_synced': [...],
     'files_already_current': [...],
     'row_count_mismatches': [...],
     'enforcement_matches': N,
     'errors': [...]
   }

Rules:
- Do NOT modify source code files
- Do NOT push to git
- Report mismatches but do NOT attempt to fix them (create a GitHub issue note instead)" \
    --max-budget-usd 0.50
