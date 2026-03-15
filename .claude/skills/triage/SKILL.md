---
name: triage
description: Aggressively scan all task sources and produce a ranked "do this next" action list
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

Scan the entire ecosystem for actionable work and produce a prioritized task list. Runs `triage-scan.sh` to collect signals, then applies LLM judgment to rank heterogeneous findings.

**Arguments:** `$ARGUMENTS`
- No argument → full scan (all 10 sources)
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

5. **Rank findings** using this priority matrix:

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
   | Convention drift (DRIFT) | P3 | Important but not urgent |
   | Code signals (TODO/FIXME) | P3 | Technical debt |
   | CHANGELOG staleness | P3 | Documentation hygiene |
   | Stale branches (>3) | P3 | Repo cleanup |

6. **Output the ranked action list** (cap at 8 items). Use this format:

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

   Clean: 6/8 repos clean | Board: 3 AI todo | Last CHANGELOG: today

   Recommended: /work kr-derivatives
   ```

   **Grouping rules:**
   - "Immediate" = P0 items (must be resolved before doing anything else)
   - "Next task" = highest-priority P1/P2 board item or backlog item
   - "Backlog surfaced" = items found in ECOSYSTEM.md backlog not on the board
   - Summary line at bottom: repo cleanliness count, board todo count, CHANGELOG status
   - Final line: single recommended next command

7. **If previous triage exists**, add a delta section:
   ```
   Delta (since last triage YYYY-MM-DD HH:MM):
     [RESOLVED] kr-beneish — was UNCOMMITTED, now clean
     [NEW]      kr-derivatives — STALE parquets detected
   ```

8. **Write triage snapshot** to `C:\Users\pon00\Projects\forensic-accounting-toolkit\triage-last.json`:
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
       "cross_issues_active": ["XB-002"]
     },
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
