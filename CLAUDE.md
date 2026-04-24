# Forensic Accounting Toolkit — Coordination Hub

This is **not a code project**. It is the orchestration layer for a multi-repo Korean forensic accounting ecosystem. All code lives in sibling directories under `C:\Users\pon00\Projects\`.

---

## The Ecosystem

Thirteen repos across four layers. Each is an independent git repo.

### Foundation Libraries (standalone, no cross-imports)

| Project | Path | Purpose | Tests |
|---------|------|---------|-------|
| **kr-company-registry** | `../kr-company-registry` | DART↔KRX↔BRN↔CRN identifier crosswalk (3,949 companies) | 18 |
| **kr-trading-calendar** | `../kr-trading-calendar` | KRX trading-day math (holidays, offsets, ranges) | 13 |
| **kr-beneish** | `../kr-beneish` | Beneish M-Score for Korean IFRS companies | 73 |
| **jfia-catalog** | `../jfia-catalog` | 469 JFIA forensic accounting articles (structured JSON) | 8 |

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
- **Per-project details**: Read the CLAUDE.md in each project's root
- **Ecosystem status**: `ECOSYSTEM.md` in this directory
- **Cross-repo operations**: `bash ecosystem.sh <command>` (see below)
- **Step-by-step workflows**: `WORKFLOW.md` in this directory
- **Local-only notes** (not for public docs): see the gitignored working directories

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
| CLAUDE.md | Present at repo root | — |

---

## Documentation Maintenance

Documentation across 13 repos drifts in two ways: **stale repo names** (old name `kr-forensic-finance` appearing in new content) and **stale test counts** (hub CLAUDE.md table falling behind as tests are added). A layered set of automatic and semi-automatic mechanisms keeps both in check.

### Design rule: where counts live

Per-repo CLAUDE.md files **do not contain test counts** — they only describe purpose, architecture, and conventions (static info). Test counts live only in the hub CLAUDE.md ecosystem table and ECOSYSTEM.md publication table, maintained by automation.

### Automatic hooks (no user action needed)

All hooks live in `.claude/hooks/` and are wired in `.claude/settings.json`.

| Hook | Event | What it does |
|------|-------|-------------|
| `post-edit-stale-check.py` | `PostToolUse/Edit` and `PostToolUse/Write` | After any file edit, greps the written content for `kr-forensic-finance`. Warns immediately with the line numbers. Fires silently when clean. |
| `post-commit-test-sync.py` | `PostToolUse/Bash` (git commit only) | After `git -C <repo> commit`, runs `pytest --co -q` and compares the count to hub CLAUDE.md. Warns with exact numbers if they diverge. |
| `stop-doc-drift-scan.sh` | `Stop` | Full sweep of all CLAUDE.md, README.md, and hub docs at session end. Reports any files still carrying stale names before the session closes. |
| `session-start.sh` + triage DOC DRIFT | `SessionStart` | On session open, `triage-scan.sh` SOURCE 8b greps the same file set and surfaces stale names as the first signal of the session. |

### Skill-based mechanisms (manual trigger, automatic execution)

| Skill / step | Trigger | What it does |
|---|---|---|
| `/done` step 5b | After task completion | Runs `pytest --co -q`, syncs count to hub CLAUDE.md + ECOSYSTEM.md, then runs the stale-name grep across all docs. |
| `/triage` SOURCE 8b | `DOC DRIFT` section | Surfaces all files with stale repo names; shows exact file paths. |
| `/plan conventions` convention #14 | Convention audit | `grep -rl "kr-forensic-finance"` across all repos; listed as a named convention violation. |

### Single sources of truth

| What | Where | Updated by |
|------|-------|-----------|
| Repo list | `ecosystem.conf` `ALL_REPOS` | Hand-edit when a repo is added/removed |
| Test counts | Hub `CLAUDE.md` ecosystem table | `post-commit-test-sync.py` warns; `/done` writes the fix |
| Publication status | `ECOSYSTEM.md` | `/done` after any publication event |
| Stale name exceptions | `post-edit-stale-check.py` and `stop-doc-drift-scan.sh` | "Previously known as" lines are explicitly excluded from warnings |

### What is NOT automated (by design)

The actual **write** step — updating hub CLAUDE.md and ECOSYSTEM.md with corrected counts — is not auto-applied. Hooks warn; humans (or `/done`) confirm and commit. This prevents silent auto-edits from writing wrong counts mid-session before tests are finalised.

---

## Documentation Model

Every doc in the ecosystem falls into exactly one of three layers:

| Layer | What | Where | Git-tracked? |
|-------|------|-------|-------------|
| **1. Repo-local public** | CLAUDE.md, README.md, `docs/` (API docs), `reports/` (run logs), `articles/` (learning content) | Each repo | Yes |
| **2. Hub local-only** | Working notes not appropriate for public repos | `knowledge/` (this hub only) | No (gitignored) |
| **3. Hub operational** | ECOSYSTEM.md, WORKFLOW.md, ARCHITECTURE.md, cross-issues/, content/captures/ | Hub root | Yes |

**Decision tree — "Where does this doc go?"**
- Needed to understand/use the code in one specific repo? → Layer 1 (that repo's `docs/` or `reports/`)
- Working notes not for public consumption? → Layer 2 (hub `knowledge/`, gitignored)
- Cross-project coordination? → Layer 3 (hub root)

Repos do **not** maintain local `knowledge/` directories.

## Knowledge Vault

The hub maintains a local-only `knowledge/` directory (gitignored) for notes that are not appropriate for the public repos — regulatory analysis, legal compliance research, and other working-notes material. This is the canonical location; per-repo `knowledge/` directories are not maintained.

### Frontmatter contract (gold standard)

```yaml
---
name: <Human-readable title>
description: <One sentence — substantive, not generic>
type: context    # or: hypothesis, bridge
domain: market-intelligence | regulatory | legal-compliance | technical | data-sources
tags: [tag1, tag2, tag3]
created: YYYY-MM-DD
last_verified: YYYY-MM-DD
related:
  - "[[other-note-stem]]"
---
```

### Navigation

- **Map of Content:** `knowledge/_index.md` — 4 question-based reading paths
- **Freshness:** notes are flagged at session start if `last_verified` > 90 days old
- **Drift check:** session end hook warns if a repo has knowledge files not mirrored to hub

---

## Hard Rules (Non-Negotiable)

### Data Integrity
- **Never modify raw DART/KRX data files.** `data/raw/` is immutable.
- **Never mix K-GAAP and K-IFRS numbers** in the same analysis. Always check the accounting standard.
- **Never extrapolate M-score** beyond the calibrated threshold. Report probability, not a verdict.
- **Split-adjustments must be applied** before any price-based ratio calculation. Use `kr-trading-calendar` for split dates.

### Code Quality
- **Always run tests before committing**: `uv run pytest tests/ -q`. All tests must pass.
- **Never modify test files to make them pass.** Fix the source code.
- **Never hardcode ticker symbols or company names.** Use the constants module.
- **All DART API calls must go through the retry wrapper.** Never call the API directly.

### Triage System
- **Never duplicate triage-scan.sh logic** in move-forward skills. Call it as a subprocess and wrap output.
- **triage-last.json** is updated by triage-scan.sh. Do not edit it manually.

### Publication Rules
- All repos are fully public. Keep repository content scoped to the engineering artifact (code, docs, reproducible data).
- Version tags follow semver.

---

## When Working in This Directory

You are in the coordination hub. Your job here is to:
1. Track cross-project blockers (not per-project bugs — those stay in each repo)
2. Maintain the ecosystem map and publication status
3. Help the human decide what to work on next across all projects

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

## Exhaust Before Escalate

Before asking the human to provide anything — a credential, a value, a decision, a command output — verify it cannot be obtained through autonomous means first.

**The question is always: "Can I find or do this myself?"**

| What's needed | Where to look first |
|---|---|
| API key or secret | `.env`, `.env.local` in project root |
| Auth token or password | `.env`, then keychain / config files (`~/.config/`, `~/.netrc`) |
| A file's contents | Read the file |
| System or tool state | Run the command (`wrangler whoami`, `gh auth status`, `git remote -v`) |
| A decision with a clear default | Apply the default; note what was assumed |

Only after these sources are exhausted — and genuinely empty — should the task pause and surface a request to the human. An AI that asks for what it could have found itself is not autonomous; it is offloading effort.

This principle has no exceptions for "convenience" or "I wasn't sure where to look." Look first. Ask only when looking fails.

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
- External correspondence sent in a personal capacity
- Web portal logins requiring 2FA (PyPI, SEIBRO registration)
- Spending money (PyPI tokens, API subscriptions)
- Deleting published repos or irreversible external actions

---

## Verification-Gated Action Policy

The autonomy question is **"has this already been verified?"** — not **"is a human watching?"**

When an action is downstream of a trusted verification gate, executing it is part of
completing the task. Asking for additional human approval at that point adds friction
without adding safety — the gate already happened.

### Act without asking when the prior gate is trusted

| Prior gate | Examples of actions that follow |
|-----------|----------------------------------|
| `verify_agent` returned `status=pass` (all tests green) | Merge the PR, push the branch, close the originating issue |
| CI is green on a commit I authored | Push to master, create a release tag |
| `fix_agent` self-verified + verify_agent confirmed | Auto-merge the PR regardless of category |
| Triage / orchestrator classified an item as AI-actionable | Execute the fix without re-asking whether to proceed |

### Still confirm before acting — no prior gate exists

| Action | Why it still requires confirmation |
|--------|-----------------------------------|
| Force-push (`--force`) to any branch | Overwrites history, no recovery |
| `git reset --hard` on a shared branch | Same |
| Dropping or truncating a data table or raw file | `data/raw/` is immutable by policy |
| Deleting a published GitHub repo, branch, or release | Irreversible, visible to external users |
| Any spend (API keys, subscriptions, tokens) | Money is the human's to authorize |

### The decision rule in one sentence

> If the action would have been the **next automatic step** in the workflow had
> everything gone right, and the verification that "everything went right" has
> already run — just do it.
