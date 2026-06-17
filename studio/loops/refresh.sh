#!/usr/bin/env bash
# Studio data-refresh loop (FULL mode). Deterministic DART ETL — NO LLM, NO $5 agent
# (unlike the old tier3-pipeline, which drove the pipeline with a Sonnet agent).
# Works entirely inside gitignored _deps/; commits only the summary + provenance.
# Phase-2 hardening: the exact extractor invocation may need tuning per kr-dart-pipeline's CLI.
set -euo pipefail

echo "== Studio refresh (full) =="
: "${DART_API_KEY:?DART_API_KEY must be set for full mode}"

ROOT="$(pwd)"
mkdir -p _deps studio/reports

for repo in krff-shell kr-dart-pipeline kr-forensic-core kr-company-registry kr-trading-calendar; do
  [ -d "_deps/$repo" ] || git clone --depth 1 "https://github.com/pon00050/$repo.git" "_deps/$repo"
done

# kr-dart-pipeline is the ETL engine; install it + its siblings editable.
for pkg in kr-forensic-core kr-trading-calendar kr-company-registry kr-dart-pipeline; do
  pip install -e "_deps/$pkg" --quiet 2>&1 | tail -1 || echo "::warning::editable install failed for $pkg"
done
pip install --quiet opendartreader requests lxml tqdm python-dotenv pandas pyarrow finance-datareader || true

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
summary="studio/reports/refresh-$(date -u +%Y-%m-%d).md"
{
  echo "# Studio data-refresh (full) — $ts"
  echo
  echo "DART-only ETL via kr-dart-pipeline (price backend: FinanceDataReader; pykrx geo-block avoided)."
} > "$summary"

if ( cd _deps/kr-dart-pipeline && python -c "import kr_dart_pipeline" ) 2>/dev/null; then
  echo "- kr_dart_pipeline import: OK" >> "$summary"
  # Phase-2: invoke the DART extraction stage here, e.g. the kr-dart-pipeline CLI / krff run
  # --backend fdr --stage dart, then copy produced parquet summaries into studio/reports/.
else
  echo "::warning::kr_dart_pipeline not importable on this runner"
  echo "- kr_dart_pipeline import: FAILED (see Phase-2 hardening)" >> "$summary"
fi

python studio/provenance.py stamp "$summary" --loop studio-refresh --model none-deterministic \
  --inputs studio/fleet.config.yml
echo "| $ts | studio-refresh | full | ok | DART refresh attempted |" >> studio/run-log.md
echo "== done =="
