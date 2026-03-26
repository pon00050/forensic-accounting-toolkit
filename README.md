# forensic-accounting-toolkit

Coordination hub for a multi-repo Korean forensic accounting ecosystem. All code lives in the component repositories listed below — this repo contains the orchestration layer: cross-project issue tracking, ecosystem status, workflow documentation, and CI scripts.

## The ecosystem

Seven repositories, one platform. Each is an independent project with its own tests, documentation, and release cycle.

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

### Platform

| Repository | Purpose |
|---|---|
| [krff-shell](https://github.com/pon00050/krff-shell) | Delivery shell: CLI, reports, review queue, DuckDB query layer, MCP server (11 tools) |

## Dependency graph

```
jfia-catalog ──► jfia-forensic ──► krff-shell
                                         ▲
kr-company-registry ─────────────────────┤
kr-trading-calendar ─────────────────────┤
kr-beneish ──────────────────────────────┤
kr-derivatives ──────────────────────────┤
kr-enforcement-cases ────────────────────┘
```

Libraries are standalone. `krff-shell` is the delivery integration point.
`kr-derivatives` reads data files from `kr-dart-pipeline` outputs (not code imports).

## What's in this repo

```
ECOSYSTEM.md          # Publication status, blockers, prioritized backlog
WORKFLOW.md           # Step-by-step command sequences for common operations
cross-issues/         # Cross-project blockers (XB-001, XB-002, ...)
ecosystem.sh          # Multi-repo git status, test runner, parquet sync
triage-scan.sh        # Automated 10-source task scanner
lessons.md            # Operational rules learned from mistakes
```

## What this project does

This toolkit applies option-pricing theory and forensic accounting techniques to Korean public company filings from [DART](https://dart.fss.or.kr/) (the Korean SEC's EDGAR equivalent). The core use case:

**Convertible bond dilution screening** — Korean convertible bonds (전환사채) and bonds with warrants (신주인수권부사채) are a known vector for minority shareholder dilution on KOSDAQ. A company issues a CB with a conversion price set below the current stock price, meaning the bondholder profits at issuance before any repricing. By treating the embedded conversion option as a European call (Black-Scholes), we can screen the entire DART dataset for suspicious issuances without needing commercial SEIBRO data.

Supporting capabilities include M-Score earnings manipulation detection (Beneish), company identifier resolution across four Korean numbering systems, trading calendar math for KRX, and a growing library of forensic accounting "detectlets" derived from JFIA academic literature.

## License

MIT
