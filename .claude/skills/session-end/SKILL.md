---
name: session-end
description: End-of-session audit — verify all repos clean, board current, nothing forgotten
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read
---

Run an end-of-session audit before the human closes the terminal. This is a read-only check.

## Steps

1. **Check all 8 repos for uncommitted changes:**
   For each repo in `C:\Users\pon00\Projects\`:
   - forensic-accounting-toolkit, kr-forensic-finance, kr-company-registry, kr-beneish,
     kr-derivatives, kr-trading-calendar, jfia-catalog, jfia-forensic
   - `git status --short` — flag any with uncommitted changes
   - `git log --oneline @{upstream}..HEAD 2>/dev/null` — flag any with unpushed commits

2. **Check the board for stale items:**
   ```bash
   "/c/Program Files/GitHub CLI/gh.exe" project item-list 1 --owner pon00050 --format json
   ```
   - Any items marked "In Progress" that should be moved to Done or back to Todo?
   - Any items that were worked on this session but still show as Todo?

3. **Check CHANGELOG.md** — was it updated if work was done today?
   Read the last entry date. If work was committed today but CHANGELOG wasn't updated, flag it.

4. **Display results as a checklist:**

   ```
   Session End Audit
   =================

   Repos:
     [OK] forensic-accounting-toolkit — clean, pushed
     [!!] kr-derivatives — 2 uncommitted changes
     [OK] kr-beneish — clean, pushed
     ...

   Board:
     [OK] No stale In Progress items
     [!!] "kr-derivatives Run 2" still Todo — was this worked on?

   Documentation:
     [OK] CHANGELOG.md updated today
     [!!] ECOSYSTEM.md last updated 2026-03-14 — check if current

   Action needed: 2 items need attention before closing.
   ```

5. If everything is clean, end with: "All clear. Safe to close."
   If issues exist, list them clearly so the human can decide what to address.

## Rules

- Read-only. Do NOT fix anything. Just report.
- Do NOT commit, push, or modify the board.
- If the human wants to fix something, they'll tell you.
- Be concise — this should be a 10-second glance, not a 5-minute report.
