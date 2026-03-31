# Agent Architecture — Forensic Accounting Toolkit

Autonomous CI/CD agent team running on GitHub Actions. Detects problems, fixes
deterministic ones in-place, dispatches Sonnet workers for reasoning-required
fixes, and escalates to the human only when necessary.

---

## Overview

The system is organized into four tiers. Each tier produces a JSON scratchpad
artifact; downstream tiers consume those artifacts without re-running upstream
work. The Orchestrator synthesizes everything into a ranked action list twice a
week and dispatches fix workers for AI-actionable items.

```
DETECT               SYNTHESIZE           FIX                 ESCALATE
──────────────────   ──────────────────   ─────────────────   ──────────
Tier 1 (bash)   ──►  Tier 2 (Haiku)  ──►  Tier 3 (Sonnet) ──►  GitHub
Tier 1 (bash)   ──►  Orchestrator    ──►  Tier 4 (Sonnet)      Issues +
                     (Sonnet)                                   Escalation
```

---

## Tier 1 — Detection (Bash, no LLM)

Five daily bash scanners. Each produces a scratchpad JSON and optionally
creates a GitHub issue. Where a deterministic fix is possible, the fix is
applied in-workflow before the issue is created.

| Workflow | Schedule (KST) | Script | Output | Autofix |
|----------|---------------|--------|--------|---------|
| `tier1-tests.yml` | 07:00 daily | matrix pytest (11 repos) | `test-results.json` | — dispatches tier4 on failure |
| `tier1-doc-drift.yml` | 08:00 daily + push `*.md` | `doc-drift-scan.sh` | `doc-drift.json` + `sibling-drift.json` | hub files: direct commit; sibling repos: PAT push |
| `tier1-count-sync.yml` | after tier1-tests | `count-sync-check.sh` | `count-sync.json` | patches `CLAUDE.md` counts, direct commit |
| `tier1-convention-check.yml` | 07:30 daily | `convention-quick-check.sh` | `convention-quick.json` | — |
| _(no workflow)_ | — | _(triage-scan.sh runs at session start locally)_ | `triage-scan-raw.txt` | — |

### Autofix scripts (`scripts/ci/`)

| Script | Input | What it patches | Exit codes |
|--------|-------|-----------------|------------|
| `autofix-count-sync.py` | `count-sync.json` | Test count column in hub `CLAUDE.md` | 0=fixed, 1=error, 2=nothing |
| `autofix-doc-drift.py` | `doc-drift.json` | Hub files (direct); writes `sibling-drift.json` for bash | 0=fixed, 1=error, 2=nothing |

### Issue creation logic (both autofix workflows)

```
scan → autofix attempt
  ├── success → commit [skip ci] + push + close stale issues → no new issue
  └── failure → create agent-task issue as before
```

`[skip ci]` in commit messages prevents push-triggered doc-drift re-runs.

---

## Tier 2 — Synthesis (Haiku LLM)

Two agents that interpret raw scan output and produce structured JSON.

### `tier2-triage.yml` — Daily triage (Haiku, $0.50 budget)

- **Trigger:** 08:30 KST daily (`schedule: 0 23:30 * * *`)
- **Input:** `triage-scan-raw.txt` (output of `triage-scan.sh`)
- **Agent:** `scripts/agents/triage_agent.py`
- **Model:** `claude-haiku-4-5-20251001`
- **Output:** `triage.json` — ranked action list (P0–P3), blocked items,
  `recommended_next` command
- **Creates:** GitHub issue labeled `agent:triage` with daily health snapshot

### `tier2-data-validate.yml` — Pipeline validation (Haiku, triggered after tier3-pipeline)

- **Trigger:** `workflow_run` after `Tier 3 — Pipeline Runner`
- **Input:** parquet files from `pipeline-parquets` artifact
- **Agent:** `scripts/agents/data_validate_agent.py`
- **Model:** `claude-haiku-4-5-20251001`
- **Output:** `data-validation.json` — per-file status (rows, schema, freshness)
- **Creates:** issue on FAIL; silent on PASS

---

## Tier 3 — Deep Analysis (Sonnet LLM)

Two weekly agents that perform deeper, more expensive analysis.

### `tier3-convention-audit.yml` — Convention audit (Sonnet, Sunday 13:00 KST)

- **Input:** all 13 repos cloned (`--depth 5`), previous audit artifact for delta
- **Agent:** `scripts/agents/convention_audit_agent.py`
- **Model:** `claude-sonnet-4-6`
- **Output:** `convention-audit.json` — 182-check audit across 14 conventions,
  new-since-last-audit delta
- **Creates:** issue labeled `agent:convention-audit`; closes previous audit issue

### `tier3-pipeline.yml` — ETL pipeline runner (Sonnet, Monday 12:00 KST)

- **Human gate:** `environment: production` — requires manual approval before run
- **Agent:** inline Sonnet agent (no separate `.py` file)
- **Model:** `claude-sonnet-4-6`, $5.00 budget, 40 turns
- **Runs:** `krff-shell` CLI pipeline in `--sample` mode (pykrx geo-blocked on CI)
- **Output:** `pipeline.json` + `pipeline-parquets` artifact
- **Triggers:** `tier2-data-validate` via `workflow_run` on completion

---

## Orchestrator — Coordinator Brain (Sonnet, Mon+Thu 15:00 KST)

The most critical agent. Synthesizes all worker outputs into a unified health
picture and creates specific, file-level action briefs.

- **Workflow:** `orchestrator.yml`
- **Agent:** `scripts/agents/orchestrator_agent.py`
- **Model:** `claude-sonnet-4-6`, $1.00 budget, 20 turns
- **Input:** downloads all 7 scratchpad artifacts from most recent workflow runs
- **Anti-pattern enforced:** never "delegate understanding" — briefs include
  exact file, line number, and command where possible
- **Output:** `orchestrator.json` — ecosystem health score, action briefs, needs_human list
- **Creates:** individual issues for P0/P1 briefs; batched issue for P2/P3
- **Dispatches:** `repository_dispatch: agent-fix` for AI-actionable P0/P1 in
  categories `CONVENTION_DRIFT`, `STUB`, `DOC_DRIFT`, `COUNT_DRIFT` (max 5/run)
- **Escalation:** writes `escalation.md` → creates `ESCALATION` issue if
  3+ P0 issues are >7 days old

---

## Tier 4 — Fix Worker (Sonnet, event-driven)

Triggered by `repository_dispatch: agent-fix` from tier1-tests or the
Orchestrator. Attempts autonomous code fix, creates PR on success.

### `tier4-autofix.yml`

- **Trigger:** `repository_dispatch` (`agent-fix`) or `workflow_dispatch`
- **Deduplication:** skips if an `autofix/*` branch PR is already open for the repo
- **Checkout:** hub + target repo (into `_target_repo/`)
- **Agent:** `scripts/agents/fix_agent.py`
- **Model:** `claude-sonnet-4-6`, $2.00 budget, 25 turns
- **Tools:** `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`
- **Hard rules enforced by agent:**
  - Never modify test files
  - Never mock out failing logic
  - Never touch `data/raw/`
  - Write `needs_human` if failure is env-dependent (missing parquets, API keys)
  - Max 3 fix attempts before giving up

### Fix result flow

```
fix_agent.py runs
  ├── status=fixed → commit to autofix/<repo>-<run_id> branch
  │                → push (requires ECOSYSTEM_PAT)
  │                → gh pr create --repo pon00050/<repo>
  │                → comment on originating issue with PR URL
  └── status=needs_human → comment on originating issue
                          → no PR, no commit
```

### Dispatch sources

| Source | Category | Trigger condition |
|--------|----------|-------------------|
| `tier1-tests.yml` | `TEST_FAIL` | Any repo fails pytest; skips if open issue exists |
| `orchestrator.yml` | `CONVENTION_DRIFT`, `STUB`, `DOC_DRIFT`, `COUNT_DRIFT` | AI-actionable P0/P1 brief; skips if open fix PR exists |

---

## Inter-Agent Communication

All agents communicate via JSON files in `$GITHUB_WORKSPACE/_scratchpad/`.
No agent calls another agent directly.

| File | Written by | Read by |
|------|------------|---------|
| `test-results.json` | tier1-tests (summary job) | orchestrator, tier4 dispatch |
| `doc-drift.json` | tier1-doc-drift | orchestrator, autofix-doc-drift.py |
| `sibling-drift.json` | autofix-doc-drift.py | tier1-doc-drift bash step |
| `count-sync.json` | tier1-count-sync | orchestrator, autofix-count-sync.py |
| `convention-quick.json` | tier1-convention-check | orchestrator |
| `triage.json` | tier2-triage | orchestrator |
| `convention-audit.json` | tier3-convention-audit | orchestrator |
| `data-validation.json` | tier2-data-validate | orchestrator |
| `pipeline.json` | tier3-pipeline | orchestrator |
| `orchestrator.json` | orchestrator | (final synthesis — creates issues + dispatches) |
| `fix-brief.json` | tier4-autofix (workflow step) | fix_agent.py |
| `fix-result.json` | fix_agent.py | tier4-autofix (PR creation step) |
| `escalation.md` | any agent on failure | orchestrator.yml (creates ESCALATION issue) |

Artifacts are uploaded with `retention-days: 90` (30 for fix scratchpads).
The Orchestrator downloads all artifacts from the most recent run of each
upstream workflow before synthesizing.

---

## Shared Infrastructure

### `scripts/agents/_sdk_helpers.py`

Shared by all agent Python scripts:
- `load_context()` — reads `CONTEXT.md` for prompt cache prefix (Principle #7)
- `write_scratchpad(filename, data)` — writes JSON with auto-timestamp
- `run_agent(prompt, options)` — runs SDK agent, retries once on failure,
  writes `escalation.md` on second failure (Principle #12)
- `collect_text(messages)` — extracts text from SDK message stream

### `scripts/agents/CONTEXT.md`

Static system prompt prefix shared by all agents. Prepended verbatim so
it hits the prompt cache on every call. Contains: repo registry, dependency
graph, 14 canonical conventions, data flow, escalation triggers, board
access instructions, scratchpad path map.

### `scripts/ci/checkout-ecosystem.sh`

Reusable symlink script. Creates `$PARENT/<repo>` → `$GITHUB_WORKSPACE/_deps/<repo>`
so that relative paths like `../kr-beneish` work identically in CI and locally.
Used by every tier1 workflow.

---

## Model Routing

| Task type | Model | Rationale |
|-----------|-------|-----------|
| Scan synthesis (triage, data validation) | `claude-haiku-4-5-20251001` | High-volume, structured output, cost-sensitive |
| Deep analysis (convention audit, orchestrator) | `claude-sonnet-4-6` | Reasoning across 13 repos, cross-reference |
| Code fixes | `claude-sonnet-4-6` | Root-cause diagnosis + targeted edit |
| Pipeline execution | `claude-sonnet-4-6` | Long multi-step task, 40 turns, $5 budget |

Claude Opus is never used — cost unjustified for these structured tasks.

---

## Required Secrets

| Secret | Used by | Purpose |
|--------|---------|---------|
| `ANTHROPIC_API_KEY` | tier2, tier3, orchestrator, tier4 | All LLM calls |
| `DART_API_KEY` | tier3-pipeline | DART Open API for financial data |
| `ECOSYSTEM_PAT` | tier1-doc-drift, tier4-autofix | Push to sibling repos + create PRs. Classic PAT, `repo` + `workflow` scopes. Without it: hub-only fixes still apply; sibling push and fix PRs skip gracefully. |

---

## Full Detect → Fix → Close Loop

```
Daily 07:00 KST
  tier1-tests fails for repo X
    → creates agent-task issue
    → dispatches repository_dispatch: agent-fix {repo: X, category: TEST_FAIL}

  tier4-autofix fires
    → checks no open autofix PR for X
    → checks out X into _target_repo/
    → fix_agent.py (Sonnet):
        reads CLAUDE.md → runs pytest → reads failing test + source
        → edits source → re-runs pytest → all pass
        → writes fix-result.json {status: fixed, changed_files: [...]}
    → commits to autofix/X-<run_id>
    → gh pr create --repo pon00050/X
    → comments on original issue with PR URL

Human reviews PR → merges → tier1-tests goes green → issue auto-closes.

Deterministic fixes (count drift, hub doc drift) skip the PR entirely:
  commit directly to master → close stale issues in same workflow step.
```

---

## Limitations and Known Gaps

| Gap | Status | Path to close |
|-----|--------|---------------|
| Sibling repo doc drift without `ECOSYSTEM_PAT` | skips gracefully, creates issue | Configure `ECOSYSTEM_PAT` |
| Fix PRs for sibling repos without `ECOSYSTEM_PAT` | skips gracefully | Configure `ECOSYSTEM_PAT` |
| pykrx geo-blocked on CI | pipeline runs in `--sample` mode | Use FinanceDataReader or self-hosted runner |
| Board access in CI (`gh project` requires `project` OAuth scope) | falls back to `board-snapshot.json` (exported at local session end) | Configure PAT with `project` scope for triage workflow |
| Convention drift autofix (structural missing files) | detected, dispatched to tier4 | tier4 handles via STUB/CONVENTION_DRIFT categories |
| Reasoning-required fixes that need external data (SEIBRO, API keys) | agent writes needs_human | Human handles per task ownership rules |
