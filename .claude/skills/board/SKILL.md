---
name: board
description: Show all open work (board + backlog) with dependency-aware execution order
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

Show all open work across the ecosystem — board items AND backlog — then produce a dependency-aware execution order. This is the "what order do I do things" command.

**Arguments:** `$ARGUMENTS` (unused, reserved for future filtering)

## Steps

### 1. Collect all open work from 3 sources

**Source A — Board items:**
```bash
"/c/Program Files/GitHub CLI/gh.exe" project item-list 1 --owner pon00050 --format json
```

**Source B — ECOSYSTEM.md backlog:**
Read `C:\Users\pon00\Projects\forensic-accounting-toolkit\ECOSYSTEM.md` and extract all unchecked `- [ ]` items with their priority section (P0/P1/P2/P3).

**Source C — Triage signals (blockers):**
Run `bash "C:/Users/pon00/Projects/forensic-accounting-toolkit/triage-scan.sh" quick 2>&1` and extract:
- Any `[STALE]` items from BOARD FRESHNESS
- Any `[UNCOMMITTED]` or `[UNPUSHED]` repos from GIT HYGIENE
- Any data sync issues (if visible in quick mode)

**Source D — Known Gaps (Unblocked):**
Read each repo's CLAUDE.md and extract `## Known Gaps` table rows with Unblocked status. These are documented gaps that may represent work not yet on the board.

### 2. Merge and deduplicate

Combine board Todo items and backlog items into a single list. Deduplicate by matching titles (board title "kr-beneish PyPI publication" matches backlog "kr-beneish PyPI publication"). When both exist, keep the richer description. Note items that appear in backlog but NOT on the board — these are "unsurfaced" and should be flagged.

### 3. Display the board view

```
=== BOARD ===

In Progress:
  (list or "none")

Todo — AI:
  [P1] kr-beneish PyPI publication
  [P1] kr-derivatives Run 4 — 32 remaining >10x moneyness outliers
  ...

Todo — Human:
  [P0] Call G1 주관기관 SNU 시흥 — deadline Mar 24
  ...

Unsurfaced (in backlog, not on board):
  [P2] kr-enforcement-cases → kr-forensic-finance label integration
  ...

Known Gaps (Unblocked, not on board):
  kr-derivatives — greeks.py zero test coverage
  kr-beneish — edge case handling for missing quarters
  ...
  (capped at 5, sorted: bug > risk > other)

Done: N items
```

### 4. Dependency analysis

Build a dependency graph for all open items using these inference rules. Check each rule against the merged task list. A dependency exists only if both tasks are open (not Done).

**Repo-level dependencies** (from CLAUDE.md dependency graph):
- Any task in `kr-forensic-finance` that changes pipeline outputs → blocks downstream tasks in `kr-derivatives` (data must be synced via `bash ecosystem.sh copy-parquets`)
- Any task in `jfia-catalog` that changes data → blocks downstream tasks in `jfia-forensic`
- Any task in a foundation library that changes its API → blocks `kr-forensic-finance` tasks that consume it

**Data-level dependencies** (from triage signals):
- If triage shows `[STALE]` parquets → any `kr-derivatives` screen run is blocked until sync
- If triage shows `[UNCOMMITTED]` in a repo → commit/push is a prerequisite before any new work in that repo

**Task-level dependencies** (pattern matching on titles/descriptions):
- "Run N" blocks "Run N+1" in the same repo (sequential iterations)
- "PyPI publication" for a repo requires: tests green, hatchling build system, README exists
- "Phase N" blocks "Phase N+1" in the same project
- Any cross-issue resolution unblocks tasks that reference that issue
- Any task that produces data consumed by another task blocks the consumer

**Cross-issue dependencies:**
- Read `cross-issues/*.md` for ACTIVE issues. Any open task that references an active cross-issue is blocked until the issue is resolved.
- Check if any active cross-issue's `Fix location` repo has an open task that would resolve it.

### 5. Produce the execution order

Assign each open item to a wave:

- **Wave 0 (blockers):** Git hygiene issues (uncommitted/unpushed), stale data that must be synced. These aren't tasks — they're prerequisites. Show as actionable commands.
- **Wave 1 (start now):** Items with no unfinished dependencies. Can run in parallel if in different repos.
- **Wave 2 (after Wave 1):** Items that depend on Wave 1 completions. Show which Wave 1 item they wait on.
- **Wave 3+:** Deeper chains if they exist.
- **Human (independent):** Human-owned tasks sorted by deadline proximity. Note any that block AI work.

```
Execution Order:

  Wave 0 (prerequisites):
    → bash ecosystem.sh copy-parquets (kr-derivatives inputs stale)
    → cd kr-beneish && git push (1 unpushed commit)

  Wave 1 (start now, parallel):
    [P1] [AI] kr-beneish PyPI publication
    [P1] [AI] kr-derivatives Run 4

  Wave 2 (after Wave 1):
    [P2] [AI] kr-enforcement-cases → kr-forensic-finance label integration
      ↳ waits on: kr-enforcement-cases GitHub publication (done) + label pipeline wiring

  Deferred (P3 / future month):
    [P3] [AI] Platform integration (Phase 4)
    [P3] [AI] Enforcement case search MCP tool #12
      ↳ waits on: kr-enforcement-cases dataset

  Human (by deadline):
    [P0] Call G1 주관기관 SNU 시흥 — deadline 2026-03-24 ⚠️ 9 days
    [P0] Send 4 LinkedIn InMails
    [P0] Apply to EY Forensic / Deloitte
    [P2] SEIBRO API: call KSD (blocks XB-002 resolution)
```

**Wave assignment rules:**
- Known Gaps with "bug" or "risk" in their status promote to Wave 1 if the repo has no other Wave 1 work
- P3 items and items with target dates >6 weeks out go to "Deferred" regardless of dependencies
- If a Human task blocks an AI task, flag it: `⚠️ blocks: [AI task title]`
- If two Wave 1 items are in the same repo, they can't truly run in parallel — note this

### 6. Recommend next action

After showing the execution order, recommend a session bundle: Wave 0 prerequisites first, then up to 3 AI-owned Wave 1 items from different repos. If a producer repo task (per DATAFLOW_* in ecosystem.conf) and a consumer repo task are both in the bundle, note that the producer must finish first with a `copy-parquets` sync in between. Flag any Human tasks that block AI work.

End with:
```
Recommended: /work [highest-priority Wave 1 AI task]
```

## Rules

- **Read-only.** Do not execute any task, modify the board, or change any files.
- Keep the board view compact — the user glances at this to decide what to work on.
- Do NOT invent dependencies that aren't supported by the inference rules. When uncertain, treat tasks as independent.
- If a dependency is ambiguous (e.g., "does Run 4 really block enforcement cases?"), note it with `(?)` rather than asserting it.
- Backlog items not on the board: flag them as "Unsurfaced" so the user can decide whether to promote them.
- If gh CLI is offline, fall back to ECOSYSTEM.md backlog only and note the limitation.
