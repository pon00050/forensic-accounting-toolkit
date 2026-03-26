# Ecosystem Status

> Last updated: 2026-03-26 (codebase review wave 1–4 complete)

---

## Publication Status

| Repo | GitHub | PyPI | Status |
|------|--------|------|--------|
| krff-shell | pon00050/krff-shell | — | Published (renamed 2026-03-26). 317 tests. SQL injection fixed; all test failures resolved. |
| kr-forensic-core | pon00050/kr-forensic-core | — | Created 2026-03-26. 10 tests. Shared foundation. |
| kr-dart-pipeline | pon00050/kr-dart-pipeline | — | Published 2026-03-26. 29 tests. 19 pipeline scripts. sys.path hacks removed. |
| kr-anomaly-scoring | pon00050/kr-anomaly-scoring | — | Published 2026-03-26. 13 tests. 8 scoring modules. sys.path hacks removed. |
| kr-stat-tests | pon00050/kr-stat-tests | — | Published 2026-03-26. 5 tests. 14 stat validation scripts. |
| kr-company-registry | pon00050/kr-company-registry | — | Published (v1.0.0, weekly auto-refresh) |
| kr-health-monitor | pon00050/kr-health-monitor | — | Published (out of toolkit scope) |
| kr-beneish | [pon00050/kr-beneish](https://github.com/pon00050/kr-beneish) | **Not published** | Published (2026-03-15). 61 tests. |
| kr-derivatives | [pon00050/kr-derivatives](https://github.com/pon00050/kr-derivatives) | **Not published** | Published (2026-03-15). 118 tests. Vega/day-count conventions documented. |
| kr-trading-calendar | [pon00050/kr-trading-calendar](https://github.com/pon00050/kr-trading-calendar) | — | Published (2026-03-15). 13 tests. Non-session snap-direction documented. |
| jfia-catalog | [pon00050/jfia-catalog](https://github.com/pon00050/jfia-catalog) | — | Published (2026-03-15). Data artifact. |
| jfia-forensic | [pon00050/jfia-forensic](https://github.com/pon00050/jfia-forensic) | **Not published** | Published (2026-03-15). 83 tests. SIGNAL_SEED_VOCABULARY synced; private attr access fixed; model ID dated. |
| kr-enforcement-cases | [pon00050/kr-enforcement-cases](https://github.com/pon00050/kr-enforcement-cases) | — | Published (2026-03-17, v1.0.0). 65 tests. 240 enforcement cases (FSS+SFC). |

---

## Cross-Project Blockers

See `cross-issues/` for details. Summary:

| ID | Title | Source | Fix Location | Status |
|----|-------|--------|-------------|--------|
| XB-001 | Split-adjusted prices needed | kr-derivatives Run 1 | kr-forensic-finance `extract_price_volume.py` | **FIXED** (2026-03-15, `9b99bfb`) |
| XB-002 | SEIBRO API resultCode=99 | kr-forensic-finance | External (공공데이터포털 revising API) | **DEFERRED** until end of April 2026 |

---

## Technical Backlog (Prioritized)

### P0 — Enables credible demo and outreach
- [x] Fix split-adjusted prices in kr-forensic-finance (XB-001) ✓ (2026-03-15)
- [x] Publish 5 repos to GitHub (beneish, derivatives, calendar, jfia-catalog, jfia-forensic) ✓ (2026-03-15)
- [x] Add CLAUDE.md to kr-trading-calendar ✓ (2026-03-15)
- [x] Commit pending README changes in kr-trading-calendar ✓ (2026-03-15)

### P1 — This month
- [x] kr-derivatives Run 2 (after XB-001 fix) ✓ (2026-03-15) — flag rate unchanged at 49.3%, identified denomination mismatch root cause
- [x] kr-derivatives Run 3 (adjust K via DART corporate actions) ✓ (2026-03-15) — flag rate 49.3% → 34.0%, extreme moneyness -87%
- [x] kr-derivatives Run 4 (resolve 32 remaining >10x moneyness outliers) ✓ (2026-03-16) — moneyness >10x: 32→4 (only GENUINE_ITM remain), flag rate 34.0%→33.1%
- [ ] kr-beneish PyPI publication

### P2 — May 2026
- [ ] Phase 3 DART reassessment (sub-document parsers: extract or keep?)
- [ ] SEIBRO API activation (DEFERRED — 공공데이터포털 revising dataset/API, ETA end of April 2026)
- [x] kr-enforcement-cases dataset ✓ (2026-03-17, v1.0.0 — 240 cases, 3 sources, 65 tests)

### P3 — June–July 2026
- [ ] Platform integration (Phase 4)
- [ ] Enforcement case search MCP tool #12

---

## Key Reference Locations

| What | Where |
|------|-------|
| Platform strategy (9 docs) | `../kr-forensic-finance/00_Reference/10_Platform_Strategy/` |
| Business strategy | `../kr-forensic-finance/00_Reference/11_Business_Outreach/` |
| kr-derivatives Run 2 plan | `../kr-derivatives/reports/second_run_prep.md` |
| kr-derivatives Run 3 lessons | `../kr-derivatives/reports/third_run_lessons.md` |
| kr-derivatives Run 4 plan | `../kr-derivatives/reports/fourth_run_prep.md` |
| kr-derivatives Run 4 lessons | `../kr-derivatives/reports/fourth_run_lessons.md` |
| Beneish calibration | `../kr-beneish/docs/calibration.md` |
| Detectlet registry | `../jfia-forensic/data/curated/detectlets/` |
| Company crosswalk data | `../kr-company-registry/data/dist/kr_corp_ids.parquet` |
| Labeled fraud cases (30) | `../kr-beneish/src/kr_beneish/data/labels.csv` |
| Enforcement violations (240) | `../kr-enforcement-cases/reports/violations.csv` |
| Enforcement Beneish ratios (60) | `../kr-enforcement-cases/reports/beneish_ratios.csv` |
| DART-matched enforcement companies (86) | `../kr-enforcement-cases/data/curated/dart_matches.csv` |
| JFIA enriched articles | `../jfia-forensic/data/curated/jfia_enriched.json` |
