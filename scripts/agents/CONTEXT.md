# Forensic Accounting Toolkit — Shared Agent Context

This file is prepended verbatim to every agent's system_prompt. It provides the
static ecosystem context that enables prompt cache reuse across all agents.

---

## Ecosystem Overview

You are operating on the **Korean forensic accounting toolkit** — a 13-repo Python
ecosystem for detecting financial fraud and misconduct in Korean public companies.
The hub repo (forensic-accounting-toolkit) is the orchestration layer. All code
lives in sibling repos under the same parent directory.

On GitHub Actions, all repos are checked out under `$GITHUB_WORKSPACE/_deps/<repo>`
and symlinked to `$parent/<repo>` so that relative paths like `../kr-beneish` work.

---

## Repo Registry (dependency order)

### Foundation Libraries (no cross-imports)
| Repo | Purpose | Tests |
|------|---------|-------|
| kr-company-registry | DART↔KRX↔BRN↔CRN identifier crosswalk (3,949 companies) | 18 |
| kr-trading-calendar | KRX trading-day math (holidays, offsets, ranges) | 13 |
| kr-beneish | Beneish M-Score for Korean IFRS companies | 61 |
| jfia-catalog | 469 JFIA forensic accounting articles (structured JSON) | 8 |

### Analysis Libraries (consume data files, not code)
| Repo | Purpose | Tests |
|------|---------|-------|
| kr-derivatives | CB/BW option pricing + ITM issuance detection | 118 |
| jfia-forensic | Detectlet schema, JFIA enrichment pipeline, signal vocabulary | 83 |
| kr-enforcement-cases | FSS/SFC enforcement case dataset + LLM enrichment pipeline | 65 |

### Platform (consumes all of the above)
| Repo | Purpose | Tests |
|------|---------|-------|
| kr-forensic-core | Shared constants, schemas, path conventions (zero deps) | 10 |
| kr-dart-pipeline | ETL: 15 extractors (DART/KRX/SEIBRO/KFTC/FSC) → parquet | 29 |
| kr-anomaly-scoring | CB/BW + timing + officer network anomaly scoring | 13 |
| kr-stat-tests | 14 statistical validation tests (PCA, bootstrap, LASSO, RF) | 5 |
| krff-shell | Delivery shell: CLI, reports, review queue, DuckDB query layer | 317 |

### Related
| Repo | Purpose |
|------|---------|
| kr-real-estate | Korean real estate market analysis (early stage) |

---

## Dependency Graph (cascade risk for test failures)

```
kr-forensic-core  ← zero deps, upstream of everything
    ↑
    ├── kr-dart-pipeline    (writes parquets)
    ├── kr-anomaly-scoring  (reads parquets)
    ├── kr-stat-tests       (reads parquets + CSVs)
    └── krff-shell          (delivery: CLI + reports)

jfia-catalog → jfia-forensic → krff-shell
kr-company-registry → krff-shell
kr-trading-calendar → krff-shell
kr-beneish → krff-shell
kr-derivatives → krff-shell (reads parquets from kr-dart-pipeline)
kr-enforcement-cases → krff-shell (enforcement labels)
```

**Test failure cascade rule:** A failure in kr-forensic-core affects ALL platform repos.
A failure in kr-dart-pipeline affects kr-anomaly-scoring, kr-stat-tests, krff-shell, kr-derivatives.

---

## Data Flow

Parquet files produced by kr-dart-pipeline and stored in:
- `krff-shell/01_Data/processed/price_volume.parquet`
- `krff-shell/01_Data/processed/cb_bw_events.parquet`
- `krff-shell/01_Data/processed/corp_actions.parquet`

These are consumed by:
- kr-derivatives (via `data/input/` symlink/copy)
- kr-anomaly-scoring (direct read)
- kr-stat-tests (direct read)

Staleness threshold: 20 days. Older than 20 days = STALE.

---

## 14 Canonical Conventions

| # | Convention | Expected | Exceptions |
|---|-----------|----------|------------|
| 1 | Build system | hatchling in [build-system] | jfia-catalog exempt |
| 2 | Python version | >=3.11 in requires-python | kr-beneish: >=3.10 OK |
| 3 | Package manager | uv only, no requirements.txt | — |
| 4 | Test command | uv run pytest tests/ -v | kr-company-registry: bare pytest OK |
| 5 | uv.lock committed | git ls-files uv.lock returns result | jfia-catalog exempt |
| 6 | conftest.py | tests/conftest.py present | Repos without tests/ exempt |
| 7 | constants.py | src/*/constants.py present | kr-trading-calendar exempt |
| 8 | Paths module | _paths.py or paths.py in src/ | Repos with no file I/O exempt |
| 9 | Commit style | feat/fix/docs/refactor/test/chore prefix | — |
| 10 | .claude/ dir | Present at repo root | jfia-catalog exempt |
| 11 | compile-bytecode | compile-bytecode = false in [tool.uv] | Repos without pyproject.toml exempt |
| 12 | CLAUDE.md | Present at repo root | — |
| 13 | Known Gaps | ## Known Gaps section in CLAUDE.md | Hub exempt |
| 14 | No stale names | Zero matches for "kr-forensic-finance" in .md/.toml/.conf | files under reports/ exempt |

Severity: OK / DRIFT (exists but wrong) / MISS (absent) / EXEMPT (documented exception)

---

## Hard Rules (Non-Negotiable)

- Never modify raw DART/KRX data files. data/raw/ is immutable.
- Never mix K-GAAP and K-IFRS numbers in the same analysis.
- Never hardcode ticker symbols or company names — use constants.py.
- All DART API calls must go through the retry wrapper.
- Never commit .env files or API keys.

---

## Escalation Triggers (stop and write escalation.md)

- Any test suite goes red after an autonomous commit
- Three consecutive failed attempts at the same task
- Any destructive git operation needed (force push, reset --hard, branch deletion)
- Any unrecognized repo structure
- Any action requiring money, 2FA login, or external communication

---

## Task Ownership

**Agent handles:** code fixes, commits, pushes, test runs, documentation updates
**Human handles:** outreach, phone calls, 2FA logins, money, PyPI publish, irreversible external actions

---

## Board Access

GitHub Projects board #1, owner pon00050:
```bash
gh project item-list 1 --owner pon00050 --format json
```

**CI fallback:** The default `GITHUB_TOKEN` lacks `project` scope, so the live
command fails on GitHub Actions. When it fails, `triage-scan.sh` reads
`board-snapshot.json` (committed to the hub root, exported at each local session
end by `stop-board-snapshot.sh`). The snapshot includes an `exported_at`
timestamp — flag it to the user if older than 48 hours.

AI-owned Todo items are the primary action queue.

---

## Scratchpad Paths (on GitHub Actions runner)

All agent outputs go to `$GITHUB_WORKSPACE/_scratchpad/`:
- `test-results.json` — from tier1-tests
- `doc-drift.json` — from tier1-doc-drift
- `convention-quick.json` — from tier1-convention-check
- `count-sync.json` — from tier1-count-sync
- `triage.json` — from tier2-triage
- `data-validation.json` — from tier2-data-validate
- `convention-audit.json` — from tier3-convention-audit
- `pipeline.json` — from tier3-pipeline
- `orchestrator.json` — from orchestrator (synthesis output)
- `escalation.md` — human-required items (triggers notification)
