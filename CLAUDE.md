# Forensic Accounting Toolkit — Coordination Hub

This is **not a code project**. It is the orchestration layer for a multi-repo Korean forensic accounting ecosystem. All code lives in sibling directories under `C:\Users\pon00\Projects\`.

---

## The Ecosystem

Seven projects, one platform. Each is an independent git repo with its own CLAUDE.md.

### Foundation Libraries (standalone, no cross-imports)

| Project | Path | Purpose | Tests |
|---------|------|---------|-------|
| **kr-company-registry** | `../kr-company-registry` | DART↔KRX↔BRN↔CRN identifier crosswalk (3,949 companies) | 18 |
| **kr-trading-calendar** | `../kr-trading-calendar` | KRX trading-day math (holidays, offsets, ranges) | 10 |
| **kr-beneish** | `../kr-beneish` | Beneish M-Score for Korean IFRS companies | 53 |
| **jfia-catalog** | `../jfia-catalog` | 469 JFIA forensic accounting articles (structured JSON) | — |

### Analysis Libraries (standalone, consume data files not code)

| Project | Path | Purpose | Tests |
|---------|------|---------|-------|
| **kr-derivatives** | `../kr-derivatives` | CB/BW option pricing + ITM issuance detection | 67 |
| **jfia-forensic** | `../jfia-forensic` | Detectlet schema, JFIA enrichment pipeline, signal vocabulary | 36 |

### Platform (consumes all of the above)

| Project | Path | Purpose | Tests |
|---------|------|---------|-------|
| **kr-forensic-finance** | `../kr-forensic-finance` | 14 extractors, 4 analysis phases, CLI, FastAPI, MCP server | 306 |

### Related (not core, potentially relevant)

| Project | Path | Purpose |
|---------|------|---------|
| **kr-real-estate** | `../kr-real-estate` | Korean real estate market analysis (early stage) |

---

## Dependency Graph

```
jfia-catalog ──► jfia-forensic ──► kr-forensic-finance (MCP tool #11)
                                          ▲
kr-company-registry ──────────────────────┤ (corp_code ↔ ticker)
kr-trading-calendar ──────────────────────┤ (trading-day math)
kr-beneish ───────────────────────────────┤ (M-Score computation)
kr-derivatives ───────────────────────────┘ (CB/BW scoring; reads parquets)
```

Libraries are standalone. kr-forensic-finance is the integration point.
kr-derivatives reads **data files** from kr-forensic-finance (not code imports).

---

## How to Navigate

- **Cross-project blockers**: `cross-issues/` in this directory
- **Business outreach & deadlines**: `knowledge/business/` (gitignored)
- **Per-project details**: Read the CLAUDE.md in each project's root
- **Platform strategy docs**: `../kr-forensic-finance/00_Reference/10_Platform_Strategy/`
- **Ecosystem status**: `ECOSYSTEM.md` in this directory

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

## Canonical Conventions (enforced by convention-auditor agent)

The full convention checklist lives in `.claude/skills/canonical-conventions/SKILL.md`.
Run `/plan conventions` to audit all repos against it. Summary:

| Convention | Expected | Exceptions |
|---|---|---|
| Build system | hatchling | jfia-catalog (data artifact) |
| Python | >=3.11 | kr-beneish (>=3.10) |
| Package manager | uv | — |
| Test command | `uv run pytest tests/ -v` | kr-forensic-finance: `python -m pytest` |
| uv.lock | Committed | jfia-catalog |
| conftest.py | Required if tests exist | — |
| constants.py | Required if magic strings exist | kr-trading-calendar |
| Paths module | `_paths.py` or `paths.py` in src | Repos with no file I/O |
| Commit style | feat/fix/docs/refactor/test/chore prefix | — |
| .claude/ directory | Present | jfia-catalog |
| compile-bytecode | `false` in `[tool.uv]` | Repos without pyproject.toml |
| CLAUDE.md | Present at repo root | — |

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
5. **Execute** the task: write code, run tests, commit with descriptive messages
6. **Update the board** status via `gh` CLI
7. **Update `ECOSYSTEM.md`** if publication status or blocker status changed
8. **Move to next item**

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
