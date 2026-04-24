# PLAN.md — Forensic Accounting Toolkit

Plans are written by AI, for AI. Their audience is other Claude instances executing the work.

---

## How to make a plan

When asked to plan a milestone:
1. Read lessons.md and ECOSYSTEM.md first
2. Ask clarifying questions until no major unknowns remain
3. Research any API or system-specific details needed
4. Write PLAN-M{N}.md with: goal, prerequisites, implementation steps, validation steps, rollback
5. Include peer review instructions in the plan file itself

## How to implement a plan

When asked to implement PLAN-M{N}.md:
1. Read lessons.md and PLAN-M{N}.md completely before writing any code
2. Follow steps in declared order — do not skip or reorder
3. After each step: validate it worked before proceeding
4. Request peer review at the step marked PEER REVIEW CHECKPOINT
5. Address all peer objections before continuing
6. Update PLAN-M{N}.md with validation results at the end

## Peer review protocol

Request a second agent's opinion by writing to a file, then asking the user to pass it to a fresh Claude:
> "Please review `review-request-M{N}.md` and give feedback on [KISS / codebase style / correctness / milestone goals]. Reply with objections only — no praise needed."

If the second agent has objections, address them all before marking the step done.

---

## Milestones

### M1 — GitHub Portfolio Publication
**Goal:** All ecosystem repos published publicly at github.com/pon00050.
**Status:** Complete — all repos published March 15-17, 2026.
**Plan file:** N/A (complete)

### M2 — kr-beneish PyPI Publication
**Goal:** kr-beneish published to PyPI as `kr-beneish`. Installable via `pip install kr-beneish`.
**Status:** P1 backlog
**Plan file:** PLAN-M2.md (create when starting)

_Note: plans that involve external correspondence or specific named counterparties
are tracked in the gitignored working directory, not in this public file._

### M5 — SEIBRO API Integration
**Goal:** Integrate SEIBRO API for CB/BW data once API is revised.
**Status:** Deferred — ETA end of April 2026
**Plan file:** Create after SEIBRO API is confirmed available

---

## Better Engineering milestone (after each M milestone)

After completing any milestone, run a "better engineering" review:
1. Ask Claude to assess the code for KISS, DRY, test coverage, documentation
2. Ask a fresh Claude to assess the first assessment
3. Review findings, make your own judgments
4. Create sub-milestones for the improvements worth making
