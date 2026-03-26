# Forensic Accounting Toolkit — Coordination Hub

This is **not a code project**. It is the orchestration layer for a multi-repo Korean forensic accounting ecosystem. All code lives in sibling directories under `C:\Users\pon00\Projects\`.

---

## The Ecosystem

Thirteen repos across four layers. Each is an independent git repo.

### Foundation Libraries (standalone, no cross-imports)

| Project | Path | Purpose | Tests |
|---------|------|---------|-------|
| **kr-company-registry** | `../kr-company-registry` | DART↔KRX↔BRN↔CRN identifier crosswalk (3,948 companies) | 18 |
| **kr-trading-calendar** | `../kr-trading-calendar` | KRX trading-day math (holidays, offsets, ranges) | 13 |
| **kr-beneish** | `../kr-beneish` | Beneish M-Score for Korean IFRS companies | 61 |
| **jfia-catalog** | `../jfia-catalog` | 469 JFIA forensic accounting articles (structured JSON) | — |

### Analysis Libraries (standalone, consume data files not code)

| Project | Path | Purpose | Tests |
|---------|------|---------|-------|
| **kr-derivatives** | `../kr-derivatives` | CB/BW option pricing + ITM issuance detection | 118 |
| **jfia-forensic** | `../jfia-forensic` | Detectlet schema, JFIA enrichment pipeline, signal vocabulary | 83 |
| **kr-enforcement-cases** | `../kr-enforcement-cases` | FSS/SFC enforcement case dataset + LLM enrichment pipeline | 65 |

### Platform (consumes all of the above)

| Project | Path | Purpose | Tests |
|---------|------|---------|-------|
| **kr-forensic-core** | `../kr-forensic-core` | Shared constants, schemas, path conventions (zero deps) | 10 |
| **kr-dart-pipeline** | `../kr-dart-pipeline` | ETL: 15 extractors (DART/KRX/SEIBRO/KFTC/FSC) → parquet | 29 |
| **kr-anomaly-scoring** | `../kr-anomaly-scoring` | CB/BW + timing + officer network anomaly scoring | 13 |
| **kr-stat-tests** | `../kr-stat-tests` | 14 statistical validation tests (PCA, bootstrap, LASSO, RF…) | 5 |
| **krff-shell** | `../krff-shell` | Delivery shell: CLI, reports, review queue, DuckDB query layer | 317 |

### Related (not core, potentially relevant)

| Project | Path | Purpose |
|---------|------|---------|
| **kr-real-estate** | `../kr-real-estate` | Korean real estate market analysis (early stage) |

---

## Dependency Graph

```
kr-forensic-core  ← shared constants, schemas, path conventions (zero external deps)
    ↑
    ├── kr-dart-pipeline       (ETL: writes parquets)
    ├── kr-anomaly-scoring     (reads parquets, uses thresholds)
    ├── kr-stat-tests          (reads parquets + CSVs)
    └── krff-shell             (delivery: CLI + reports + review queue)

jfia-catalog ──► jfia-forensic ──► krff-shell (MCP tool #11)
                                        ▲
kr-company-registry ────────────────────┤ (corp_code ↔ ticker)
kr-trading-calendar ────────────────────┤ (trading-day math)
kr-beneish ─────────────────────────────┤ (M-Score computation)
kr-derivatives ─────────────────────────┤ (CB/BW scoring; reads parquets from kr-dart-pipeline)
kr-enforcement-cases ───────────────────┘ (enforcement labels; future MCP tool #12)
```

Data flow: kr-dart-pipeline writes parquets → kr-anomaly-scoring + kr-stat-tests + krff-shell read them.
kr-derivatives reads parquet **data files** from kr-dart-pipeline outputs (not code imports).
kr-enforcement-cases produces **enforcement labels** for supervised model training in krff-shell.

---

## How to Navigate

- **Cross-project blockers**: `cross-issues/` in this directory
- **Business outreach & deadlines**: `knowledge/business/` (gitignored)
- **Per-project details**: Read the CLAUDE.md in each project's root
- **Platform strategy docs**: `../krff-shell/00_Reference/10_Platform_Strategy/`
- **Ecosystem status**: `ECOSYSTEM.md` in this directory
- **Cross-repo operations**: `bash ecosystem.sh <command>` (see below)
- **Step-by-step workflows**: `WORKFLOW.md` in this directory

---

## Cross-Repo Operations (`ecosystem.sh`)

The hub contains `ecosystem.sh` for common multi-repo tasks. Run from the hub directory:

```bash
bash ecosystem.sh test-all          # Run tests in all repos, report pass/fail
bash ecosystem.sh test <repo>       # Run tests in one repo
bash ecosystem.sh status            # Git status across all repos
bash ecosystem.sh copy-parquets     # Copy krff-shell outputs → kr-derivatives inputs
bash ecosystem.sh unpushed          # Show repos with unpushed commits
```

**When to use:**
- `copy-parquets` — before any kr-derivatives screen run (ensures input data is current)
- `status` / `unpushed` — before pushing, at session end, or when unsure what's committed where
- `test-all` — after dependency upgrades or convention changes touching multiple repos

---

## Conventions (apply to all projects)

- **Package manager**: `uv` (never pip)
- **Python**: 3.11+ (3.10+ for kr-beneish)
- **Testing**: `uv run pytest tests/ -v`
- **Git**: Never amend published commits. New commits only.
- **Claude API model routing**: Haiku for classification, Sonnet for synthesis, never Opus
- **Data files**: Parquet for pipeline artifacts, CSV for human-readable outputs
- **Constants**: All magic strings/thresholds in `constants.py` per project
- **Paths**: All paths in `_paths.py` or `paths.py` per project

---

## Skills Reference

Skills are invoked with `/skill-name`. They live in `.claude/skills/`.

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `/triage` | Start of session (auto), or "what needs doing?" | Scans 10 sources (board, git, data freshness, code signals, conventions, backlog) and ranks next actions |
| `/board` | "What should I work on?" or "what order?" | Merges board + backlog, builds dependency graph, produces wave-based execution order |
| `/plan` | Before starting non-trivial work, or "analyze the ecosystem" | 5-layer ecosystem analysis: board state, repo health, convention drift, integration gaps, strategic alignment |
| `/plan conventions` | After code changes across repos, or convention audit needed | Full convention checklist audit via convention-auditor agent |
| `/diagnose-moneyness` | **After any kr-derivatives screen run that produces outliers with moneyness >10x** | Queries DART API for CB filings and corporate actions, checks pykrx adjusted vs unadjusted prices, classifies each case as SPLIT_ARTIFACT / GENUINE_ITM / DATA_ERROR / INCONCLUSIVE |
| `/work` | "Work on it" or picking a task from the board | Executes the next AI task autonomously |
| `/done` | After completing a task | Updates board status, ECOSYSTEM.md, syncs counts, cascade scan for new/unblocked work |
| `/capture` | After content-worthy work, or when `/done` suggests it | Writes structured record to `content/captures/` |
| `/content` | "Show content pipeline" or reviewing what's been captured | Displays captures, drafts, and ideas with status |
| `/ecosystem-status` | "What's the status?" | Shows publication and blocker status |

### When to use `/diagnose-moneyness`

This skill exists because **adjusted stock prices and unadjusted DART exercise prices can be in different denominations** for stocks that underwent reverse splits or share consolidations. This is a recurring data quality issue in the CB/BW issuance dilution screen (kr-derivatives `examples/02_issuance_dilution_screen.py`).

**Run it when:**
- A screen run shows flag rate >40% (likely contaminated by false extreme moneyness)
- Any CB case shows moneyness >10x (economically implausible for a genuine issuance)
- After regenerating `price_volume.parquet` with new pykrx settings
- When validating that a price data fix actually resolved the denomination mismatch

**It will NOT:**
- Fix any code or data (read-only diagnostic)
- Work fully if pykrx `adjusted=False` is broken (marks cases as INCONCLUSIVE)

---

## Canonical Conventions (enforced by convention-auditor agent)

The full convention checklist lives in `.claude/skills/canonical-conventions/SKILL.md`.
Run `/plan conventions` to audit all repos against it. Summary:

| Convention | Expected | Exceptions |
|---|---|---|
| Build system | hatchling | jfia-catalog (data artifact) |
| Python | >=3.11 | kr-beneish (>=3.10) |
| Package manager | uv | — |
| Test command | `uv run pytest tests/ -v` | — |
| uv.lock | Committed | jfia-catalog |
| conftest.py | Required if tests exist | — |
| constants.py | Required if magic strings exist | kr-trading-calendar |
| Paths module | `_paths.py` or `paths.py` in src | Repos with no file I/O |
| Commit style | feat/fix/docs/refactor/test/chore prefix | — |
| .claude/ directory | Present | jfia-catalog |
| compile-bytecode | `false` in `[tool.uv]` | Repos without pyproject.toml |
| CLAUDE.md | Present at repo root | kr-forensic-core, kr-dart-pipeline, kr-anomaly-scoring, kr-stat-tests (missing; to be added) |

---

## When Working in This Directory

You are in the coordination hub. Your job here is to:
1. Track cross-project blockers (not per-project bugs — those stay in each repo)
2. Maintain the ecosystem map and publication status
3. Track business outreach tasks and deadlines
4. Help the human decide what to work on next across all projects

Do NOT write code here. Do NOT duplicate information that belongs in a sub-project's own docs.
When you need to understand a sub-project, read its CLAUDE.md first.

---

## AI Autonomy Protocol

How the AI agent works through tasks autonomously:

1. **Read the board:**
   ```bash
   "/c/Program Files/GitHub CLI/gh.exe" project item-list 1 --owner pon00050 --format json
   ```
2. **Filter** to `Owner == AI`, `Status != Done`, sort by priority (P0 first)
3. **Pick** the next unblocked item, `cd` to the correct project directory
4. **Read** that project's `CLAUDE.md` first — it contains install, test, architecture, and conventions
5. **Pre-flight**: if the task involves kr-derivatives screen runs, run `bash ecosystem.sh copy-parquets` first to sync pipeline outputs
6. **Execute** the task: write code, run tests, commit with descriptive messages
7. **Update the board** status via `gh` CLI
8. **Update `ECOSYSTEM.md`** if publication status or blocker status changed
9. **Post-flight**: `bash ecosystem.sh unpushed` to verify nothing was left behind
10. **Move to next item**

If anything unexpected is encountered (test failure, missing file, structure mismatch), document it in `CHANGELOG.md` before proceeding — never silently work around it.

---

## Task Ownership Rules

### AI handles
- Code fixes, file creation, refactoring
- Git operations (`commit`, `push`, `branch`)
- GitHub operations (`gh repo create`, `gh project` updates, `gh issue`)
- Running tests and pipelines
- Updating documentation (`CLAUDE.md`, `ECOSYSTEM.md`, `CHANGELOG.md`)

### Human handles
- Phone calls (KSD, government agencies)
- LinkedIn/email outreach (InMails, job applications)
- Web portal logins requiring 2FA (PyPI, SEIBRO registration)
- Spending money (PyPI tokens, API subscriptions)
- Deleting published repos or irreversible external actions
