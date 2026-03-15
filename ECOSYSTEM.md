# Ecosystem Status

> Last updated: 2026-03-15

---

## Publication Status

| Repo | GitHub | PyPI | Status |
|------|--------|------|--------|
| kr-forensic-finance | pon00050/kr-forensic-finance | — | Published (102 commits, 2 stars) |
| kr-company-registry | pon00050/kr-company-registry | — | Published (v1.0.0, weekly auto-refresh) |
| kr-health-monitor | pon00050/kr-health-monitor | — | Published (out of toolkit scope) |
| kr-beneish | [pon00050/kr-beneish](https://github.com/pon00050/kr-beneish) | **Not published** | Published (2026-03-15). 61 tests. |
| kr-derivatives | [pon00050/kr-derivatives](https://github.com/pon00050/kr-derivatives) | **Not published** | Published (2026-03-15). 79 tests. |
| kr-trading-calendar | [pon00050/kr-trading-calendar](https://github.com/pon00050/kr-trading-calendar) | — | Published (2026-03-15). 10 tests. |
| jfia-catalog | [pon00050/jfia-catalog](https://github.com/pon00050/jfia-catalog) | — | Published (2026-03-15). Data artifact. |
| jfia-forensic | [pon00050/jfia-forensic](https://github.com/pon00050/jfia-forensic) | **Not published** | Published (2026-03-15). 76 tests. |

---

## Cross-Project Blockers

See `cross-issues/` for details. Summary:

| ID | Title | Source | Fix Location | Status |
|----|-------|--------|-------------|--------|
| XB-001 | Split-adjusted prices needed | kr-derivatives Run 1 | kr-forensic-finance `extract_price_volume.py` | **ACTIVE** |
| XB-002 | SEIBRO API resultCode=99 | kr-forensic-finance | External (KSD approval) | **ACTIVE** (non-critical) |

---

## Technical Backlog (Prioritized)

### P0 — Enables credible demo and outreach
- [ ] Fix split-adjusted prices in kr-forensic-finance (XB-001)
- [x] Publish 5 repos to GitHub (beneish, derivatives, calendar, jfia-catalog, jfia-forensic) ✓ (2026-03-15)
- [x] Add CLAUDE.md to kr-trading-calendar ✓ (2026-03-15)
- [x] Commit pending README changes in kr-trading-calendar ✓ (2026-03-15)

### P1 — This month
- [ ] kr-derivatives Run 2 (after XB-001 fix)
- [ ] kr-beneish PyPI publication

### P2 — May 2026
- [ ] Phase 3 DART reassessment (sub-document parsers: extract or keep?)
- [ ] SEIBRO API approval (call KSD 051-519-1420)
- [ ] kr-enforcement-cases dataset

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
| Beneish calibration | `../kr-beneish/docs/calibration.md` |
| Detectlet registry | `../jfia-forensic/data/curated/detectlets/` |
| Company crosswalk data | `../kr-company-registry/data/dist/kr_corp_ids.parquet` |
| Labeled fraud cases (30) | `../kr-beneish/src/kr_beneish/data/labels.csv` |
| JFIA enriched articles | `../jfia-forensic/data/curated/jfia_enriched.json` |
