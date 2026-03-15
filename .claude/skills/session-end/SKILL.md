---
name: session-end
description: End-of-session audit — verify all repos clean, board current, nothing forgotten
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Glob
---

Run an end-of-session audit before the human closes the terminal. This is a read-only check.

## Steps

1. **Check all repos for uncommitted/unpushed changes:**
   ```bash
   bash ecosystem.sh status
   ```
   This checks all 8 repos for uncommitted changes and unpushed commits in one command.
   If the script is unavailable, fall back to manual iteration over repos in `C:\Users\pon00\Projects\`.

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

6. **Uncaptured content review.**
   Check `content/captures/` for files created today. Compare against the session's
   work (commits made today across all repos, board items moved to Done).

   If significant work was done but no captures exist for it:
   ```
   Content:
     [!!] Session involved notable work with no content capture:
          - {repo}: {description of work} ({content-worthy pattern})
          Consider: /capture {title}
   ```

   If captures already cover the session's work, or the session was routine:
   ```
   Content:
     [OK] N captures created this session
   ```

   Keep this section brief — 2-3 lines max. It's informational, not blocking.

## Rules

- Read-only. Do NOT fix anything. Just report.
- Do NOT commit, push, or modify the board.
- If the human wants to fix something, they'll tell you.
- Be concise — this should be a 10-second glance, not a 5-minute report.
