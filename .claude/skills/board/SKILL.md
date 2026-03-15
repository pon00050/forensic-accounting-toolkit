---
name: board
description: Show the GitHub Project board filtered by AI tasks and priority
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read
---

Read the GitHub Project board and display a clear summary for the human.

## Steps

1. Fetch the board:
   ```bash
   "/c/Program Files/GitHub CLI/gh.exe" project item-list 1 --owner pon00050 --format json
   ```

2. Parse the JSON and display items grouped by status, sorted by priority within each group:

   **In Progress** (if any)
   **Todo — AI owned** (sorted P0 first)
   **Todo — Human owned** (sorted P0 first)
   **Done** (collapsed count only, e.g. "6 items done")

3. For each Todo item, show: priority, title, owner. If an item has a body with useful context (like an issue description), mention the key detail in one line.

4. **Suggested Execution Order**

   After the board display, analyze remaining Todo items and produce a wave-based execution plan.

   **Known dependencies** (A must finish before B):
   - "Migrate kr-beneish to hatchling" must finish before "kr-beneish PyPI publication"
   - "Fix: split-adjusted prices" must finish before "kr-derivatives Run 2"
   - Any "Add conftest.py" task must finish before "Increase test coverage" in the same repo
   - Any "Migrate to hatchling" task must finish before PyPI publication for that repo

   **Scheduling rules:**
   - Group remaining Todo items into waves based on the dependency list above
   - Wave 1 = items with no unfinished dependencies (can start now)
   - Wave 2 = items that depend on Wave 1 completions
   - Wave 3+ = deeper dependencies if they exist
   - Items in the same wave but in different repos can run in parallel
   - Show Human tasks separately, sorted by deadline proximity

   Display as:
   ```
   Execution Order:
     Wave 1 (parallel): [items with no blockers]
     Wave 2 (after Wave 1): [items that depend on Wave 1]
     Human (independent): [human tasks sorted by deadline]
   ```

5. End with: "Next unblocked AI task: [title]. Say 'work on it' or pick something else. Run `/plan` for deeper analysis of emergent tasks not on this board."

## Rules

- Do NOT execute any task. This is read-only.
- Do NOT modify the board.
- Keep output concise — the human glances at this to decide what to work on.
- When new board items are added that have dependencies, update the "Known dependencies" list above.
