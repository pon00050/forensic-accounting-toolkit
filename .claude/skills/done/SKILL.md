---
name: done
description: Complete a board task — commit, push, update board status, log to CHANGELOG
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Glob
---

Wrap up a completed board task with full bookkeeping. The argument `$ARGUMENTS` is the task title or keyword to match on the board (optional — if omitted, infer from recent work context).

## Steps

1. **Identify the task.** If `$ARGUMENTS` is provided, search the board for a matching item. If not, infer from the current working directory and recent commits what was just completed.

2. **Verify the work is done in the sub-repo:**
   - `git status --short` — all changes committed?
   - If uncommitted changes exist, ask the human whether to commit them first
   - If tests exist for this repo, run them and confirm green
   - `git push` if not already pushed

3. **Update the board item:**
   ```bash
   "/c/Program Files/GitHub CLI/gh.exe" project item-edit --project-id PVT_kwHOAH3il84BRykI --id <ITEM_ID> --field-id PVTSSF_lAHOAH3il84BRykIzg_g5JA --single-select-option-id 98236657
   ```
   (Status field → Done)

4. **Log to CHANGELOG.md** in `C:\Users\pon00\Projects\forensic-accounting-toolkit\CHANGELOG.md`:
   - Add an entry under the current date section
   - Include: what was done, which repo, specific files changed, test results
   - Match the existing CHANGELOG format

5. **Check if ECOSYSTEM.md needs updating** in `C:\Users\pon00\Projects\forensic-accounting-toolkit\ECOSYSTEM.md`:
   - Did a blocker get resolved? (XB-001, XB-002)
   - Did publication status change?
   - Did a backlog item get completed?
   - If yes, update it. If no, skip.

5b. **Sync hub CLAUDE.md counts.** After updating ECOSYSTEM.md, verify test counts and extractor counts are current:
   - Run `uv run pytest tests/ --co -q` in the completed repo. Parse the test count from the last line.
   - Compare to the count shown in hub `CLAUDE.md` ecosystem table. If different, update the number.
   - Also check ECOSYSTEM.md publication table for the same repo's test count — update it to match if different.
   - If the repo is krff-shell (delivery shell), also count `.py` files matching `kr-dart-pipeline/kr_dart_pipeline/extract_*.py`. If the count differs from CLAUDE.md's "N extractors" claim, update it.
   - Only touch CLAUDE.md and ECOSYSTEM.md if a number actually changed.
   - **Stale name check**: After any file edit in this session, run:
     ```bash
     grep -rl "kr-forensic-finance" /c/Users/pon00/Projects/*/CLAUDE.md /c/Users/pon00/Projects/*/README.md /c/Users/pon00/Projects/forensic-accounting-toolkit/*.md /c/Users/pon00/Projects/forensic-accounting-toolkit/*.conf 2>/dev/null | grep -v ".git" | grep -v "reports/"
     ```
     If any files are returned, replace `kr-forensic-finance` with `krff-shell` in those files (excluding historical reports/ directories).

5c. **Sync cross-issue files.** If the completed task resolves a cross-issue:
   - Update `cross-issues/XB-NNN.md` status from ACTIVE to RESOLVED with date and commit hash
   - Example: `**Status**: RESOLVED (2026-03-15, commit \`abc1234\`)`

6. **Commit and push the toolkit hub** (CHANGELOG.md, ECOSYSTEM.md, CLAUDE.md, cross-issues changes)

7. **Report summary:**
   - What was closed
   - Board status
   - One-line "Next unblocked AI task: ..." suggestion
   - "Run /triage to rescan for newly unblocked tasks."

8. **Content assessment.** Review what was just completed and assess whether it
   involved any of these content-worthy patterns:

   - A plan or approach failed and we pivoted to an alternative
   - A new API endpoint, data source, or technique was discovered
   - A significant metric improvement was achieved (quantify: before → after)
   - A multi-step debugging or investigation sequence resolved
   - A cross-repo integration issue was identified and fixed
   - A domain-specific insight emerged (regulatory, accounting, market structure)

   If NONE match: skip silently. Do not mention content at all.

   If ANY match: suggest ONE specific /capture command at the end of the report.
   Format:

   ```
   Content: This task involved [pattern]. Consider:
     /capture {suggested-title}
   ```

   Do NOT auto-run /capture. The human decides.

9. **Cascade scan.** After all bookkeeping, actively search for new work created or unblocked by the completion. Check these 6 sources:

   | Source | What to check | How |
   |--------|--------------|-----|
   | Downstream data | Did this change data files consumed by other repos? | Check if any parquets in `kr-forensic-finance/01_Data/processed/` are newer than copies in `kr-derivatives/data/input/`. If so: `[DATA REFRESH]` |
   | Test ripple | Did downstream tests break? | Run `uv run pytest tests/ -x -q` in repos that consume outputs from the changed repo. If failures: `[TEST FAILURE]` |
   | Convention drift | Did the change introduce convention violations? | Quick check: new files without constants.py patterns, new extractors not counted, missing conftest.py. If drift: `[CONVENTION]` |
   | Unblocked items | Did this unblock board items or backlog items? | Check board Todo and ECOSYSTEM.md backlog for items that reference the completed task or its repo. If unblocked: `[UNBLOCKED]` |
   | New TODOs | Did the committed code introduce new TODOs? | `git diff HEAD~1 HEAD` in the repo, grep for TODO/FIXME/HACK. If new: `[NEW TODO]` |
   | Cross-issue cascade | Did resolving a cross-issue unblock other work? | Check `cross-issues/` for items that reference the resolved issue. If unblocked: `[CROSS-ISSUE]` |
   | Known Gaps resolved | Did completed work resolve a Known Gap? | Compare files touched and tests added against the target repo's `## Known Gaps` table in CLAUDE.md. If a gap appears resolved: `[KNOWN GAP RESOLVED]` — suggest removing or updating the row |

   Output format (appended to the report):

   ```
   Cascade scan:
     [UNBLOCKED] kr-derivatives Run 4 — XB-001 resolved, Run 3 complete
     [DATA REFRESH] kr-derivatives inputs may need sync → bash ecosystem.sh copy-parquets
     [CLEAN] No new TODOs, no test failures, no convention drift

   Discovered tasks: 1
     → kr-derivatives Run 4 (resolve 32 remaining >10x moneyness outliers)

   Recommended: /work kr-derivatives
   ```

   If cascade finds nothing: `Cascade: clean — no new tasks discovered.`

   Skip sources that clearly don't apply (e.g., don't check downstream data if the task was documentation-only). Only run downstream tests if the change modified code or data files, not docs.

10. **Lessons check.** If the task involved fixing a mistake that the system made (stale data echoed, wrong recommendation, convention violation missed), append a one-line lesson to `C:\Users\pon00\Projects\forensic-accounting-toolkit\lessons.md` with the date and what was learned. Only add lessons for systemic issues — not one-off bugs. Format:

    ```
    - **Lesson title.** Description of the rule. (Learned: YYYY-MM-DD, context)
    ```

## Board Reference

- Project ID: `PVT_kwHOAH3il84BRykI`
- Status field: `PVTSSF_lAHOAH3il84BRykIzg_g5JA`
- Done option: `98236657`
- In Progress option: `47fc9ee4`
- Owner field: `PVTSSF_lAHOAH3il84BRykIzg_g-mo`
- Fetch items: `"/c/Program Files/GitHub CLI/gh.exe" project item-list 1 --owner pon00050 --format json`

## Rules

- Always ask before committing uncommitted changes — don't assume they're ready
- If tests fail, stop and report. Do not mark the task as Done.
- CHANGELOG entries must be specific: "Fixed X in Y" not "Updated code"
- Do not over-update ECOSYSTEM.md — only touch it if status actually changed
