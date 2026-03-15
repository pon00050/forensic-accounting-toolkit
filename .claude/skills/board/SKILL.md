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

4. End with a one-line suggestion: "Next unblocked AI task: [title]. Say 'work on it' or pick something else."

## Rules

- Do NOT execute any task. This is read-only.
- Do NOT modify the board.
- Keep output concise — the human glances at this to decide what to work on.
