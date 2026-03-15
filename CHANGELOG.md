# Changelog — Forensic Accounting Toolkit

Audit trail for ecosystem-wide changes coordinated from this hub.

---

## 2026-03-15 — Ecosystem Standardization

### Phase 0: Toolkit Hub
- Updated `CLAUDE.md` with AI Autonomy Protocol and Task Ownership Rules
- Created `CHANGELOG.md` (this file) for standardization audit trail
- Updated `.obsidian/app.json`: added `"business"` to userIgnoreFilters

### Phase 1: Project Standardization (7 repos)

**kr-trading-calendar** (most work — was missing CLAUDE.md, .obsidian, knowledge/)
- Created `CLAUDE.md`: install, test, architecture (3 XKRX wrapper functions), ecosystem section
- Created `.obsidian/app.json` with userIgnoreFilters
- Created `knowledge/context/` directory (gitignored)
- `.gitignore` already had `knowledge/` and `.obsidian/` — no changes needed
- Committed pending `README.md` changes from prior session
- 10 tests pass

**jfia-catalog** (was missing .gitignore, CLAUDE.md, .obsidian, knowledge/)
- Created `.gitignore`: knowledge/, .venv/, __pycache__, .env, .claude/, .obsidian/
- Created `CLAUDE.md`: architecture (scraper → JSON catalog), ecosystem section
- Created `.obsidian/app.json` and `knowledge/context/` (gitignored)
- No tests (data artifact)

**kr-beneish** (minor updates)
- Updated `.obsidian/app.json`: added `.claude`, `.git` to userIgnoreFilters
- Added ecosystem section to `CLAUDE.md`
- Committed 8 modified + 1 untracked file from prior sessions (docs, src, tests)
- 61 tests pass

**kr-derivatives** (minor updates)
- Added `issuance_dilution_scores.csv` to `.gitignore` (pipeline output)
- Added ecosystem section to `CLAUDE.md`
- Committed pending work: calendar module, rates, examples, reports, new test_rates
- 79 tests pass

**jfia-forensic** (minor updates)
- Added ecosystem section to `CLAUDE.md`
- Committed pending work: downloader.py, normalise.py, 3 new test files, enriched data updates
- 76 tests pass

**kr-company-registry** (minor updates)
- Created `.obsidian/app.json` (gitignored via existing .gitignore)
- Added ecosystem section to `CLAUDE.md`
- Pushed to GitHub
- Tests not re-run (no code changes)

**kr-forensic-finance** (platform)
- Created `.obsidian/app.json` (gitignored)
- Created `knowledge/context/` directory (gitignored)
- Added `knowledge/`, `.obsidian/`, `outreach/` to `.gitignore`
- Added ecosystem section to root `CLAUDE.md` (was untracked, now committed)
- `outreach/` left in place (gitignored) — contains platform-specific demo materials
- Pushed to GitHub

**Architectural decisions documented (no action taken):**
- kr-company-registry stays on `main` branch
- kr-beneish stays on Python >=3.10
- kr-beneish setuptools→hatchling deferred to Phase 4
- jfia-catalog stays without pyproject.toml (data artifact)
- kr-forensic-finance keeps `00_Reference/` pattern (not replaced by `knowledge/`)
