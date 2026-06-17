# forensic-accounting-toolkit

Coordination hub for a multi-repo Korean forensic accounting ecosystem. All code lives in the component repositories listed below — this repo contains the orchestration layer: cross-project issue tracking, ecosystem status, workflow documentation, and CI scripts.

> **Status (2026-06-17):** shelved from active development; autonomous internal-only upkeep runs via the **Forensic Studio** (`studio/`). New here or resuming? Read **`RESUMING.md`** first.

## The ecosystem

Thirteen repositories, one platform. Each is an independent project with its own tests, documentation, and release cycle.

### Foundation libraries

| Repository | Purpose |
|---|---|
| [kr-company-registry](https://github.com/pon00050/kr-company-registry) | DART, KRX, BRN, and CRN identifier crosswalk (3,949 companies) |
| [kr-trading-calendar](https://github.com/pon00050/kr-trading-calendar) | KRX trading-day math — holidays, offsets, date ranges |
| [kr-beneish](https://github.com/pon00050/kr-beneish) | Beneish M-Score computation for Korean IFRS companies |
| [jfia-catalog](https://github.com/pon00050/jfia-catalog) | 469 JFIA forensic accounting articles as structured JSON |

### Analysis libraries

| Repository | Purpose |
|---|---|
| [kr-derivatives](https://github.com/pon00050/kr-derivatives) | CB/BW embedded option pricing and ITM issuance detection |
| [jfia-forensic](https://github.com/pon00050/jfia-forensic) | Detectlet schema, JFIA enrichment pipeline, signal vocabulary |
| [kr-enforcement-cases](https://github.com/pon00050/kr-enforcement-cases) | FSS/SFC enforcement case dataset + LLM enrichment pipeline |

### Platform

| Repository | Purpose |
|---|---|
| [kr-forensic-core](https://github.com/pon00050/kr-forensic-core) | Shared constants, schemas, and path conventions (zero dependencies) |
| [kr-dart-pipeline](https://github.com/pon00050/kr-dart-pipeline) | ETL: 15 extractors (DART/KRX/SEIBRO/KFTC/FSC) → standardized parquets |
| [kr-anomaly-scoring](https://github.com/pon00050/kr-anomaly-scoring) | CB/BW + timing + officer network anomaly scoring |
| [kr-stat-tests](https://github.com/pon00050/kr-stat-tests) | 14 statistical validation tests (PCA, bootstrap, LASSO, RF…) |
| [krff-shell](https://github.com/pon00050/krff-shell) | Delivery shell: CLI, reports, review queue, DuckDB query layer, MCP server (11 tools) |

## Dependency graph

```
kr-forensic-core  ← shared constants, schemas, path conventions (zero external deps)
    ↑
    ├── kr-dart-pipeline       (ETL: writes parquets)
    ├── kr-anomaly-scoring     (reads parquets, uses thresholds)
    ├── kr-stat-tests          (reads parquets + CSVs)
    └── krff-shell             (delivery: CLI + reports + review queue)

jfia-catalog ──► jfia-forensic ──► krff-shell (MCP server, 11 tools)
                                        ▲
kr-company-registry ────────────────────┤ (corp_code ↔ ticker)
kr-trading-calendar ────────────────────┤ (trading-day math)
kr-beneish ─────────────────────────────┤ (M-Score computation)
kr-derivatives ─────────────────────────┤ (CB/BW scoring; reads parquets from kr-dart-pipeline)
kr-enforcement-cases ───────────────────┘ (enforcement labels; future supervised training)
```

Data flow: `kr-dart-pipeline` writes parquets → `kr-anomaly-scoring`, `kr-stat-tests`, and `krff-shell` read them.
`kr-derivatives` reads parquet data files from `kr-dart-pipeline` outputs (not code imports).
`kr-enforcement-cases` produces enforcement labels for supervised model training in `krff-shell`.

## What's in this repo

```
RESUMING.md           # START HERE if resuming — current operational state (shelved + Studio)
ECOSYSTEM.md          # Publication status, blockers, prioritized backlog
WORKFLOW.md           # Step-by-step command sequences for common operations
studio/               # Forensic Studio — self-running internal-only upkeep (see studio/README.md)
AGENT_TEAM_REDESIGN.md # Design of the autonomous studio + adversarial review
CHANGELOG.md          # Audit trail of ecosystem changes
cross-issues/         # Cross-project blockers (XB-001, XB-002, ...)
ecosystem.sh          # Multi-repo git status, test runner, parquet sync
triage-scan.sh        # Automated 10-source task scanner
lessons.md            # Operational rules learned from mistakes
```

## What this project does

This toolkit applies option-pricing theory and forensic accounting techniques to Korean public company filings from [DART](https://dart.fss.or.kr/) (the Korean SEC's EDGAR equivalent). The core use case:

**Convertible bond dilution screening** — Korean convertible bonds (전환사채) and bonds with warrants (신주인수권부사채) are a known vector for minority shareholder dilution on KOSDAQ. A company issues a CB with a conversion price set below the current stock price, meaning the bondholder profits at issuance before any repricing. By treating the embedded conversion option as a European call (Black-Scholes), we can screen the entire DART dataset for suspicious issuances without needing commercial SEIBRO data.

Supporting capabilities include M-Score earnings manipulation detection (Beneish), company identifier resolution across four Korean numbering systems, trading calendar math for KRX, and a growing library of forensic accounting "detectlets" derived from JFIA academic literature.

## Write-ups

Each component has its own stand-alone write-up. The full case study is at
[ronanwrites.vercel.app/projects/forensic-accounting-toolkit](https://ronanwrites.vercel.app/projects/forensic-accounting-toolkit).

| Component | Write-up |
|---|---|
| `kr-company-registry` | [3,949 Companies. Four Numbering Systems. One Table.](https://ronanwrites.vercel.app/manuals/korean-company-identifier-crosswalk) |
| `kr-trading-calendar` | [60 Calendar Days Is 38 Trading Days.](https://ronanwrites.vercel.app/manuals/korean-trading-day-math) |
| `kr-beneish` | [The Beneish M-Score, Reimplemented for Korean IFRS.](https://ronanwrites.vercel.app/manuals/beneish-mscore-korean-ifrs) |
| `jfia-catalog` | [Sixteen Years of Forensic Accounting Research, in One JSON File.](https://ronanwrites.vercel.app/manuals/jfia-catalog-469-articles) |
| `kr-derivatives` | [Pricing Convertible-Bond Dilution Without SEIBRO.](https://ronanwrites.vercel.app/manuals/cb-bw-dilution-screen-without-seibro) |
| `jfia-forensic` | [Detectlets: Compiling Forensic Accounting Research Into Computable Detection Modules.](https://ronanwrites.vercel.app/manuals/jfia-detectlets-from-literature-to-code) |
| `kr-enforcement-cases` | [240 Korean Accounting Violations, Coded Once.](https://ronanwrites.vercel.app/manuals/korean-enforcement-cases) |
| Platform (4 repos) | [Splitting a Forensic-Finance Monolith into Four Repos.](https://ronanwrites.vercel.app/manuals/forensic-platform-architecture) |
| `krff-shell` | [An MCP Server for Korean Forensic Finance.](https://ronanwrites.vercel.app/manuals/krff-shell-mcp-natural-language-finance) |

## License

MIT
