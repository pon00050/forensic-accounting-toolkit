---
name: triage
description: Aggressively scan all task sources and produce a ranked "do this next" action list
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

Scan the entire ecosystem for actionable work and produce a prioritized task list. Runs `triage-scan.sh` to collect signals, then applies LLM judgment to rank heterogeneous findings.

**Arguments:** `$ARGUMENTS`
- No argument → full scan (all 13 sources)
- `quick` → fast scan (sources 1-3 only: board, git hygiene, backlog)

## Steps

1. **Run the scanner:**
   ```bash
   bash "C:/Users/pon00/Projects/forensic-accounting-toolkit/triage-scan.sh" $ARGUMENTS
   ```
   If `$ARGUMENTS` is empty, run without arguments (full mode).

2. **Check for previous triage snapshot** (for delta reporting):
   Read `C:\Users\pon00\Projects\forensic-accounting-toolkit\triage-last.json` if it exists.
   If it exists, note the timestamp and previous top findings for comparison.

3. **Parse each section** of the scanner output and classify findings.

4. **Validate board freshness.** The board is a *claim* about what needs doing. The filesystem is *evidence* of what's been done. Claims go stale. Evidence doesn't. For each board Todo/In Progress item:
   - Cross-reference the item's title against **recent commits** (shown as `~` lines in GIT HYGIENE). If commits show the described work was already completed, the board item is stale.
   - Check for **progress artifacts** in the relevant repo — e.g., `reports/` directories with run logs, prep files, or lesson files that indicate iterations beyond what the board title describes.
   - Check whether the **backlog** (ECOSYSTEM.md) describes a *later* iteration of the same task. If so, the backlog is more current than the board.
   - Mark stale items as `[STALE BOARD]` in your output. Do NOT recommend them as next tasks.
   - If a board item is stale, recommend updating it (rename or close) as a housekeeping item.

5. **Gap synthesis.** Go beyond reporting status — discover new work. Using the
   IMPLEMENTATION COMPLETENESS and STRATEGY ALIGNMENT scanner sections:

   a. **Separate blocked from actionable.** Stubs tagged [BLOCKED] go to "Blocked
      (informational)" — never recommend these. [OPEN] stubs are candidates.

   b. **Cross-reference against board and backlog.** If a gap is already tracked,
      don't surface it again. Only surface gaps that are NOT already tracked anywhere.

   c. **Assess strategic importance.** Not every gap is worth filling now:
      - Does this gap block other work? (high priority)
      - Is this gap in a repo that's otherwise "complete"? (high value — finishing repos)
      - Does strategy docs mention this as needed? (alignment signal)
      - Is this a stub in active code vs. dead/unused code? (active = higher)

   d. **Generate task descriptions.** For the top gaps (max 3), write a one-line task
      suitable for the board: repo, what's missing, why it matters.

   e. **Cross-reference Source 13 (Known Gaps).** For each Unblocked Known Gap:
      - Skip if already tracked on the board or backlog
      - Prefer the Known Gap description over raw grep stubs when both exist for the same issue
      - Boost priority for gaps whose status contains "bug" or "risk" suffixes

   f. **Output** in "Gaps discovered" section. If none: "No new gaps found."

6. **Rank findings** using this priority matrix:

   | Category | Priority | Rationale |
   |----------|----------|-----------|
   | Test failure detected | P0 | Broken code blocks everything |
   | Uncommitted changes | P0 | Risk of lost work |
   | Unpushed commits | P1 | Work done but not backed up |
   | Board P0 tasks (AI-owned, unblocked) | P1 | Explicitly prioritized |
   | Data sync staleness (STALE parquets) | P1 | Downstream results are wrong |
   | Cross-issue newly resolved | P2 | Unblocks downstream work |
   | Board P1 tasks (AI-owned, unblocked) | P2 | High priority |
   | Backlog P1 not on board | P2 | Needs board promotion |
   | Open stub in active code | P2 | Completeness of working system |
   | Strategy-mentioned but untracked | P3 | Future alignment |
   | Known Gap — Unblocked (bug/risk) | P2 | Documented gap with severity signal |
   | Known Gap — Unblocked (other) | P3 | Documented gap, no severity signal |
   | Convention drift (DRIFT) | P3 | Important but not urgent |
   | Code signals (TODO/FIXME) | P3 | Technical debt |
   | CHANGELOG staleness | P3 | Documentation hygiene |
   | Stale branches (>3) | P3 | Repo cleanup |

7. **Output the ranked action list** (cap at 8 items). Use this format:

   ```
   === TRIAGE ===

   Immediate (do before anything else):
     1. [UNCOMMITTED] kr-derivatives — 2 files modified
     2. [DATA STALE]  kr-derivatives — price_volume.parquet older than source
                      -> Run: bash ecosystem.sh copy-parquets

   Next task:
     3. [BOARD P1]    kr-derivatives Run 4 — 32 remaining outliers
                      -> /work kr-derivatives

   Backlog surfaced:
     4. [BACKLOG P1]  kr-beneish PyPI publication — not on board

   Gaps discovered:
     5. [OPEN STUB]   kr-derivatives — repricing engine has NotImplementedError
                      Why: core functionality, blocked only by SEIBRO data
     6. [INTEGRATION] kr-enforcement-cases — enforcement labels not yet consumed by krff-shell
                      Why: violations.csv exists but label pipeline not wired

   Blocked (informational):
     - kr-derivatives — SVI fitting: requires KRX options data (Phase 2)

   Clean: 6/8 repos clean | Board: 3 AI todo | Last CHANGELOG: today

   Recommended: /work kr-derivatives
   ```

   **Grouping rules:**
   - "Immediate" = P0 items (must be resolved before doing anything else)
   - "Next task" = highest-priority P1/P2 board item or backlog item
   - "Backlog surfaced" = items found in ECOSYSTEM.md backlog not on the board
   - "Gaps discovered" = new work found by sources 11-12, not already tracked
   - "Blocked (informational)" = stubs/gaps requiring human action, never recommended
   - Summary line at bottom: repo cleanliness count, board todo count, CHANGELOG status
   - Final line: single recommended next command

8. **If previous triage exists**, add a delta section:
   ```
   Delta (since last triage YYYY-MM-DD HH:MM):
     [RESOLVED] kr-beneish — was UNCOMMITTED, now clean
     [NEW]      kr-derivatives — STALE parquets detected
   ```

9. **Write triage snapshot** to `C:\Users\pon00\Projects\forensic-accounting-toolkit\triage-last.json`:
   ```json
   {
     "timestamp": "2026-03-15T14:30:00",
     "mode": "full",
     "findings": {
       "uncommitted": ["repo1"],
       "unpushed": ["repo2"],
       "stale_data": ["price_volume.parquet"],
       "board_todo": 3,
       "backlog_open": 5,
       "code_signals": 12,
       "convention_drift": [],
       "cross_issues_active": ["XB-002"],
       "open_stubs": 3,
       "blocked_stubs": 1,
       "strategy_untracked": 9
     },
     "known_gaps_unblocked": 0,
     "top_task": "kr-derivatives Run 4",
     "recommended_command": "/work kr-derivatives"
   }
   ```

## Rules

- **Read-only.** Do not fix, commit, push, or modify anything. Just report.
- Cap output at 8 ranked items. If more exist, mention count: "... and N more P3 items"
- If scanner fails entirely, report the error and suggest `bash ecosystem.sh status` as fallback.
- If gh CLI is offline, the board section will say UNAVAILABLE — continue with other sources.
- Be concise. The user wants a 15-second scan, not a 5-minute report.
- Always end with a single `Recommended:` line — the one command to run next.
