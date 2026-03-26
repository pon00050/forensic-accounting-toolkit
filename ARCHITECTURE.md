# Korean Forensic Accounting Ecosystem — Architecture Diagram

> Generated: 2026-03-26
> 13 repos · 11 code packages · ~732 tests

---

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    KOREAN FORENSIC ACCOUNTING ECOSYSTEM                                  ║
║                    13 repos · 11 code packages · ~732 tests                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL DATA SOURCES                                                                  │
│                                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │     DART     │  │     KRX      │  │     KFTC     │  │   FSC    │  │   SEIBRO    │  │
│  │  (filings,   │  │  (prices,    │  │  (payment    │  │ (company │  │ (bondholder │  │
│  │   CB/BW      │  │   volume,    │  │   data)      │  │  regs)   │  │  register)  │  │
│  │  disclosures)│  │   corp acts) │  │              │  │          │  │  [DEFERRED] │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  └──────┬──────┘  │
└─────────┼─────────────────┼─────────────────┼───────────────┼───────────────┼──────────┘
          └─────────────────┴─────────────────┴───────────────┴───────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  ETL LAYER — kr-dart-pipeline  (15 extractors)                                          │
│                                                                                         │
│  extract_price_volume   extract_cb_bw      extract_dart       extract_disclosures       │
│  extract_corp_actions   extract_krx        extract_kftc       extract_major_holders     │
│  extract_officer_holdings  extract_corp_ticker_map  extract_bondholder_register         │
│  extract_depreciation_schedule  extract_revenue_schedule  build_isin_map  …            │
│                                                                                         │
│  Output → 01_Data/processed/*.parquet (15 files)                                        │
└──────────────────────────────────────┬──────────────────────────────────────────────────┘
                                       │  parquet files
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
┌─────────────────────┐   ┌───────────────────────┐   ┌────────────────────────────────┐
│  kr-anomaly-scoring │   │    kr-stat-tests       │   │     kr-derivatives             │
│  (8 scoring modules)│   │  (14 stat validators)  │   │  (reads parquets as data files)│
│                     │   │                        │   │                                │
│  beneish_screen     │   │  pca_beneish           │   │  CB/BW option pricing          │
│  cb_bw_timelines    │   │  lasso_beneish         │   │  ITM issuance detection        │
│  timing_anomalies   │   │  rf_feature_importance │   │  moneyness scoring             │
│  officer_network    │   │  bootstrap_threshold   │   │  dilution screen               │
│                     │   │  fdr_timing_anomalies  │   │  (118 tests)                   │
│  → beneish_scores   │   │  survival_repricing    │   │                                │
│    .parquet         │   │  cluster_peers  …      │   └────────────────────────────────┘
└──────────┬──────────┘   └───────────┬────────────┘
           │                          │
           └──────────────┬───────────┘
                          │
┌─────────────────────────┼───────────────────────────────────────────────────────────────┐
│  SHARED FOUNDATION — kr-forensic-core  (zero external deps)                             │
│                                                                                         │
│   constants.py   BENEISH_THRESHOLD=-1.78, CB/BW flag names, PRICE_WINDOW=60 days       │
│   schemas.py     Pydantic schemas shared across all platform repos                      │
│   paths.py       Canonical path conventions                                             │
│                                                                                         │
│   ← imported by kr-dart-pipeline, kr-anomaly-scoring, kr-stat-tests, krff-shell        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  DELIVERY SHELL — krff-shell  (317 tests)                                               │
│                                                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────────────────────┐ │
│  │   CLI (krff)    │  │   DuckDB Layer   │  │   FastAPI + MCP Server (11 tools)      │ │
│  │                 │  │                  │  │                                        │ │
│  │  krff refresh   │  │  db.py           │  │  mcp_server.py  (FastMCP)              │ │
│  │  krff status    │  │  query()         │  │  mcp_utils.py   (JSON serialization)   │ │
│  │  krff audit     │  │  read_table()    │  │  app.py         (mounted at /mcp/)     │ │
│  │  krff analyze   │  │  (in-memory,     │  │                                        │ │
│  │  krff stats     │  │   no .duckdb)    │  │  tools: search_companies, get_scores,  │ │
│  │  krff quality   │  │                  │  │  get_disclosures, get_enforcement …    │ │
│  │  krff queue/    │  └──────────────────┘  └────────────────────────────────────────┘ │
│  │  surface/hide/  │                                                                    │
│  │  assess         │  ┌──────────────────┐  ┌────────────────────────────────────────┐ │
│  │                 │  │   HTML Reports   │  │   Review Queue (SQLite)                │ │
│  └─────────────────┘  │                  │  │                                        │ │
│                        │  report.py       │  │  review.py                             │ │
│                        │  charts.py       │  │  per-company flag workflow             │ │
│                        │  → beneish_viz   │  │  queue / surface / hide / assess       │ │
│                        │    .html         │  │                                        │ │
│                        │  Claude API for  │  └────────────────────────────────────────┘ │
│                        │  narrative       │                                              │
│                        └──────────────────┘                                              │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────── KNOWLEDGE LAYER ────────────────────────────────┐
│                                                                                         │
│  ┌──────────────────────┐   ┌──────────────────────┐   ┌───────────────────────────┐   │
│  │   jfia-catalog       │   │    jfia-forensic      │   │   kr-enforcement-cases    │   │
│  │                      │   │                       │   │                           │   │
│  │  469 JFIA forensic   │──▶│  Detectlet schema     │──▶│  240 FSS/SFC enforcement  │   │
│  │  accounting articles │   │  JFIA enrichment      │   │  cases with LLM labels    │   │
│  │  (2009–2025, JSON)   │   │  signal vocabulary    │   │  Beneish ratios (60 cos.) │   │
│  │                      │   │  (83 tests)           │   │  DART-matched (86 cos.)   │   │
│  └──────────────────────┘   └──────────────────────┘   └───────────────────────────┘   │
│                                         │                            │                  │
│                    MCP tool #11 ────────┘          MCP tool #12 ────┘  [P3, planned]   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────── IDENTIFIER LAYER ───────────────────────────────┐
│                                                                                         │
│  ┌──────────────────────────────────────┐   ┌──────────────────────────────────────┐   │
│  │       kr-company-registry            │   │       kr-trading-calendar            │   │
│  │                                      │   │                                      │   │
│  │  3,948 companies                     │   │  KRX trading-day math                │   │
│  │  DART corp_code ↔ KRX ticker         │   │  holidays, offsets, ranges           │   │
│  │  ↔ BRN ↔ CRN crosswalk              │   │  is_trading_day(), offset()          │   │
│  │  (18 tests)                          │   │  (13 tests)                          │   │
│  └───────────────────┬──────────────────┘   └──────────────────┬───────────────────┘   │
│                      │                                          │                       │
│                      └──────────────────┬───────────────────────┘                      │
│                                         │  consumed by krff-shell                      │
└─────────────────────────────────────────┼───────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼───────────────────────────────────────────────┐
│  FRAUD SCORING LIBRARY — kr-beneish     │                                               │
│                                         │                                               │
│  Beneish M-Score for Korean IFRS        │  reads: company_financials.parquet            │
│  8-ratio model (DSRI, GMI, AQI…)       │  writes: beneish_scores.parquet               │
│  labeled fraud dataset (30 companies)   │  threshold: -1.78 (from kr-forensic-core)     │
│  (61 tests)                             │                                               │
└─────────────────────────────────────────┼───────────────────────────────────────────────┘
                                          ▼
                          ┌───────────────────────────┐
                          │   krff-shell consumes all  │
                          │   of the above             │
                          └───────────────────────────┘

════════════════════════════ DATA FLOW SUMMARY ════════════════════════════

  DART/KRX/KFTC/FSC
       │
       ▼
  kr-dart-pipeline  ──────────────────────────────────────────────────────────────────┐
  (15 extractors)                                                                      │
       │ 15 *.parquet files                                                            │
       ├──────────────────► kr-anomaly-scoring  ──► beneish_scores.parquet ──► krff-shell
       ├──────────────────► kr-stat-tests       ──► validation reports     ──► krff-shell
       └──────────────────► kr-derivatives      ──► CB/BW flags            ──► (standalone)

  kr-forensic-core   ──► (imported as dep by pipeline, scoring, stats, shell)
  kr-company-registry ──► (corp_code↔ticker lookups inside krff-shell)
  kr-trading-calendar ──► (date math inside krff-shell)
  kr-beneish         ──► (M-Score computation inside krff-shell)
  jfia-catalog
       └──► jfia-forensic ──► MCP tool #11 inside krff-shell
  kr-enforcement-cases ──► enforcement labels ──► supervised ML in krff-shell
                                               └──► MCP tool #12 [planned]

  krff-shell  ──► CLI  /  HTML reports (Claude API narrative)  /  MCP server (11 tools)
                   /  DuckDB query layer  /  SQLite review queue
```

---

## Layer Summary

| Layer | Repos | What happens |
|-------|-------|-------------|
| **External sources** | — | DART filings, KRX prices, KFTC payment data, FSC company records |
| **ETL** | kr-dart-pipeline | Pulls all sources → 15 `.parquet` files |
| **Scoring** | kr-anomaly-scoring | Reads parquets → CB/BW + Beneish + officer network flags |
| **Validation** | kr-stat-tests | 14 statistical tests (PCA, LASSO, bootstrap, survival…) against the same parquets |
| **Shared foundation** | kr-forensic-core | Constants/schemas imported by all three layers above |
| **Delivery** | krff-shell | CLI, HTML reports (Claude API narrative), DuckDB query layer, FastMCP server (11 tools), SQLite review queue |
| **Knowledge** | jfia-catalog → jfia-forensic → MCP #11; kr-enforcement-cases → MCP #12 [planned] | Structured article corpus + detectlet enrichment + enforcement case labels |
| **Identifiers** | kr-company-registry, kr-trading-calendar | Crosswalk (DART↔KRX↔BRN↔CRN) and trading-day math, consumed by krff-shell |
| **Fraud scoring** | kr-beneish | Beneish M-Score for Korean IFRS, consumed by krff-shell |

## Repo Quick Reference

| Repo | Tests | Role |
|------|-------|------|
| kr-forensic-core | 10 | Zero-dep shared constants, schemas, paths |
| kr-dart-pipeline | 29 | ETL: 15 extractors → parquets |
| kr-anomaly-scoring | 13 | CB/BW + timing + officer network scoring |
| kr-stat-tests | 5 | 14 statistical validation scripts |
| krff-shell | 317 | CLI + reports + MCP server + review queue |
| kr-company-registry | 18 | 3,948-company identifier crosswalk |
| kr-trading-calendar | 13 | KRX trading-day math |
| kr-beneish | 61 | Beneish M-Score (Korean IFRS) |
| kr-derivatives | 118 | CB/BW option pricing + ITM detection |
| jfia-catalog | — | 469 JFIA articles (data artifact) |
| jfia-forensic | 83 | Detectlet schema + JFIA enrichment pipeline |
| kr-enforcement-cases | 65 | 240 FSS/SFC enforcement cases + LLM labels |
