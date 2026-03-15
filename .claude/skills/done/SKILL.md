---
name: done
description: Complete a board task — commit, push, update board status, log to CHANGELOG
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write
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

6. **Commit and push the toolkit hub** (CHANGELOG.md and ECOSYSTEM.md changes)

7. **Report summary:**
   - What was closed
   - Board status
   - One-line "Next unblocked AI task: ..." suggestion

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
