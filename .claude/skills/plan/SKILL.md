---
name: plan
description: Analyze the full ecosystem and surface what needs doing next — including emergent tasks not on the board
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob, Agent
---

Analyze the ecosystem and produce an actionable plan. This is a read-only operation — do NOT fix anything, do NOT add board items, do NOT modify files.

## Arguments

- No argument: Run all 5 analysis layers
- `conventions`: Run only the convention audit layer with full detail

## Analysis Layers

### If argument is `conventions`:

Spawn the `convention-auditor` agent and wait for its result. Display the full convention audit table. Done.

### If no argument (full analysis):

Run these 5 layers, parallelizing where possible:

**Layer 1 — Board State** (parallel with 2 and 3)

Fetch the board:
```bash
"/c/Program Files/GitHub CLI/gh.exe" project item-list 1 --owner pon00050 --format json
```

Check for:
- Items stuck In Progress for >7 days (stale)
- Items recently moved to Todo that were previously Blocked
- Total counts by status and owner

**Layer 2 — Repo Health** (parallel with 1 and 3)

For each repo in `C:\Users\pon00\Projects\` (kr-forensic-finance, kr-company-registry, kr-beneish, kr-derivatives, kr-trading-calendar, jfia-catalog, jfia-forensic, kr-real-estate):

```bash
git -C ../REPO status --porcelain
git -C ../REPO log --oneline -1 --format="%cr"
git -C ../REPO rev-list --count @{u}..HEAD 2>/dev/null  # unpushed commits
```

Flag:
- Uncommitted changes
- Unpushed commits
- Stale repos (no commits in 14+ days)
- Known Gaps with "bug" or "risk" in status suffix (code quality signal)
- Repos missing a `## Known Gaps` section in CLAUDE.md (convention drift)

**Layer 3 — Convention Drift** (parallel with 1 and 2, via background agent)

Spawn the `convention-auditor` agent in the background:
```
Use Agent tool with subagent_type convention-auditor, run_in_background: true
```

Continue with layers 1-2 while this runs. Incorporate results at the end.

**Layer 4 — Integration Gaps** (after layers 1-2)

Check across repos:
- Repos with `tests/` but no `conftest.py`
- Repos with `src/` but no `_paths.py` or `paths.py`
- Repos where CLAUDE.md references a test command that doesn't match the actual test structure
- kr-derivatives data path consistency with kr-forensic-finance outputs

Use Glob and Grep across `C:\Users\pon00\Projects\*`.

**Layer 5 — Strategic Alignment** (last, synthesizes everything)

Read `ECOSYSTEM.md` in the hub. Cross-reference with board state from Layer 1:
- Are there ECOSYSTEM.md backlog items not on the board?
- Are there board items that are newly unblocked (dependencies completed)?
- What P1/P2 items could be started now?

## Output Format

```
=== Ecosystem Plan ===

Board: X todo (Y AI, Z human), W done
Health: X/8 repos clean, Y need attention

Emergent Tasks (not on board):
  1. [HIGH] description — repo — rationale
  2. [MED]  description — repo — rationale
  ...

Suggested Next Session:
  AI: [specific task] — [why now]
  Human: [specific task] — [deadline if any]

Convention Drift: X deviations found (Y since last audit)
  [summary table from convention-auditor]
```

## Rules

- **Report only.** Do NOT fix anything, do NOT add board items, do NOT modify any files.
- **Be specific.** Emergent tasks must include the repo, the file(s) affected, and why it matters.
- **Prioritize actionability.** Don't list 20 minor things. Surface the 3-5 most impactful items.
- **Convention audit details** go in the convention drift section. Keep the main output focused on emergent tasks and next-session suggestions.
