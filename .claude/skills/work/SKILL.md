---
name: work
description: Switch working context to a specific ecosystem repo
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

Switch to a specific repo and load its context so the human can immediately give instructions.

The argument `$ARGUMENTS` is the repo name (e.g., `kr-beneish`, `kr-derivatives`, `jfia-forensic`).

## Steps

1. **Resolve the path**: The repo lives at `C:\Users\pon00\Projects/$ARGUMENTS/`. If the directory doesn't exist, list available repos and ask the user to pick one.

2. **cd to the repo**:
   ```bash
   cd /c/Users/pon00/Projects/$ARGUMENTS
   ```

3. **Read CLAUDE.md** in the repo root to load project context.

3b. **Show Known Gaps.** Extract the `## Known Gaps` table from CLAUDE.md (if present) and display it. Highlight any Unblocked items that relate to the current task or repo area.

4. **Show git status**: `git status --short` — any uncommitted changes.

5. **Show recent commits**: `git log --oneline -5` — what happened last.

6. **Run tests** (if the project has tests):
   - kr-forensic-finance: `uv run python -m pytest tests/ -x -q`
   - kr-beneish: `uv run pytest tests/ -v`
   - kr-derivatives: `uv run python -m pytest tests/ -v`
   - kr-trading-calendar: `uv run pytest tests/ -v`
   - jfia-forensic: `uv run python -m pytest tests/ -v`
   - kr-company-registry: `pytest tests/`
   - jfia-catalog: no tests
   - forensic-accounting-toolkit: no tests

7. **Summarize** in 2-3 lines: project purpose, current state, anything needing attention.

## Rules

- This skill loads context. Do NOT start working on tasks unless the human asks.
- If tests fail, report the failures clearly — do not try to fix them.
- Keep the summary brief. The human knows these projects.
