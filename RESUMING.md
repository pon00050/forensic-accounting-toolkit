# Resuming forensic-accounting-toolkit

> **Shelved 2026-06-17.** This file is the single entry point for picking the project
> back up. Read it first, then `ECOSYSTEM.md` for publication/backlog detail and
> `README.md` for the architecture.

This is the coordination hub for a 13-repo Korean forensic-accounting ecosystem.
All code lives in sibling repos under `../`. The hub holds cross-project status,
the CI orchestration layer, and (gitignored) working notes.

---

## Forensic Studio — LIVE (autonomous, internal-only)

As of 2026-06-17 the project is **shelved from active development but running autonomously** via the
**Forensic Studio** (`studio/`, design in `AGENT_TEAM_REDESIGN.md`). It is **ON now**
(`FLEET_ENABLED=true`) and runs two weekly, gated loops at **$0** (free public-repo CI, no LLM). Each
run self-bumps `studio/state/LAST_CHECKIN`, so while enabled it stays alive and the repo stays active
(GitHub never auto-disables the schedules).

**What runs today (real, deterministic):**
- **studio-maintain** — writes a discovery report of the refinement backlog AND performs a real
  **doc-count reconciliation** (rewrites stale `N tests` figures in ECOSYSTEM.md to match the
  authoritative hub CLAUDE.md), committing the fix.
- **studio-refresh** — a liveness/plumbing check that commits a dated, provenance-stamped status note.

**Scaffolded but NOT yet implemented (be honest with yourself when you return):**
- The **full DART ETL** (`studio/loops/refresh.sh`, mode=full, needs `DART_API_KEY`) currently only
  *imports* the pipeline — it does **not** refresh parquets yet. Parquets stay ~100 days stale until built.
- The **LLM fix→verify→auto-merge crew** (studio-maintain mode=full, needs `ANTHROPIC_API_KEY`) is a
  no-op placeholder (Phase 3). Adding the secret alone does nothing until the engine body is written
  (it would reuse `scripts/agents/fix_agent.py` → `verify_agent.py`).

Every run passes a **fail-closed heartbeat gate** (master switch + dead-man's-switch). Outputs are
provenance-stamped, machine-generated/unreviewed; nothing is published as a forensic conclusion
(internal-only posture). Transient failures are swallowed (`continue-on-error`) so a blip never emails.

**Controls (the only human touchpoints):**
- **Pause instantly:** `gh variable set FLEET_ENABLED --body false` (loops become green no-op skips).
  If paused >~60 days, GitHub auto-disables the schedules; to resume, `gh workflow enable` both studio
  workflows AND set `FLEET_ENABLED=true`.
- **Make it actually deliver (finish the engines):** implement the `refresh.sh` ETL body + the
  studio-maintain LLM execute step, add `DART_API_KEY` / `ANTHROPIC_API_KEY` (or a
  `CLAUDE_CODE_OAUTH_TOKEN`), and set the Anthropic workspace ceiling (~$25 backstop; expected
  $5–20/mo once the LLM crew runs). See `studio/README.md` and `AGENT_TEAM_REDESIGN.md` §cost.

---

## Health snapshot at shelving

- **All 13 repos pass their tests.** ~752 tests total — 435 across the 11 library repos plus
  **krff-shell's 317** — all green (matches the hub CLAUDE.md ecosystem table).
  - krff-shell gotcha: its MCP tests need the dev optional-extra. For local runs use
    **`uv sync --extra dev`** before `pytest` (CI already does this). Without the extra,
    11 async MCP tests error with "no plugin handled async fixture" — that is an
    environment artifact, **not** a code defect.
- **Nothing unpushed.** Every repo's local `HEAD` matched its GitHub remote at shelving.
- **Parquets are stale (~100 days).** Expected — the ETL hasn't run since early April.
  Not a defect; regenerate with `uv run krff run` from krff-shell when resuming data work.

---

## What this shelving pass changed (2026-06-17)

**1. CI automation fully quieted.** It had been emailing recurring failures and burning
daily Anthropic API spend on a project no longer being worked.
   - Root cause of the failure emails: the weekly **"Tier 3 — Pipeline Runner"** cron
     landed on a `production` environment **required-reviewer gate**, waited ~30 days
     with no approval, then failed on timeout — every cycle.
   - Removed all `schedule:` crons from the 11 scheduled workflows (kept `workflow_dispatch`
     and event triggers). Each edit is marked with a dated `# schedule cron removed
     2026-06-17` comment showing exactly where the cron was.
   - Removed the `production` approval gate from `tier3-pipeline.yml` and **deleted the
     `production` GitHub environment**.
   - **Disabled all 15 workflows** via `gh workflow disable` (immediate backstop; the
     YAML edits are the durable, source-visible record).
   - Cancelled the run that was waiting on approval (it would have emailed a failure
     ~mid-July).

**2. Folder tidy + leak-gap closure.**
   - Gitignored `.wrangler/`, `cloudflare-worker/.wrangler/` (held the Cloudflare account
     id/name), and `*.eml`.
   - Moved local-only notes out of the tracked tree into gitignored `knowledge/`:
     `PORTFOLIO_REFRAME_2026Q2.md` → `knowledge/business/positioning/`;
     `docs/strategy/*` → `knowledge/context/market-intelligence/`. Removed the empty `docs/`.
   - Deleted two GitHub-notification `.eml` files.
   - Fixed a CLAUDE.md doc/reality mismatch (`content/` is gitignored Layer-2, not tracked
     Layer-3).

---

## To re-enable everything (if you resume active work)

1. **Re-enable workflows** (all, or pick the ones you want):
   ```bash
   for f in .github/workflows/*.yml; do
     gh workflow enable "$(basename "$f")" --repo pon00050/forensic-accounting-toolkit
   done
   ```
2. **Restore schedule crons** — search the workflows for `schedule cron removed 2026-06-17`;
   each marks where to re-add the `schedule:`/`cron:` lines.
3. **Tier 3 approval gate** — recreate the `production` environment + reviewer rule *only*
   if you actually want the manual pipeline gate. Leaving it off is recommended: it was the
   sole source of the failure emails. If you re-add it, also add a short `wait-timer`/
   shorter retention so an unapproved run fails fast instead of after 30 days.
4. **Telegram bot** — the Cloudflare Worker in `cloudflare-worker/` is still deployed but its
   CI polling is off. To fully retire it: `cd cloudflare-worker && wrangler login && wrangler delete`.
   (Skipped in this pass — needs interactive Cloudflare auth.)
5. **krff-shell local dev** — `uv sync --extra dev` before running its test suite.

---

## Next immediate steps (open roadmap)

From the `ECOSYSTEM.md` technical backlog, ranked for a return:

1. **SEIBRO API activation (blocker XB-002).** Was deferred to "end of April 2026" pending
   공공데이터포털's API revision — that date has passed, so the first move on resuming is to
   re-check whether the dataset/API is live (verify externally before building), then wire it
   into `kr-dart-pipeline`. See `cross-issues/XB-002-seibro-api-blocked.md`.
2. **Enforcement case search — MCP tool #12.** Most "ready to build": the integration is
   already sketched in `../kr-enforcement-cases/reports/mcp-integration-plan.md`.
3. **Phase 3 DART reassessment.** Decide whether to extract DART sub-document parsers or keep
   current coverage.
4. **Platform integration (Phase 4).** Wire `kr-enforcement-cases` enforcement labels into
   krff-shell supervised training (see `../kr-enforcement-cases/reports/ml-feasibility-and-next-steps.md`).
5. **kr-beneish PyPI publication.** Deliberately deferred — only when you want the package
   on PyPI.

---

## Loose ends not actioned (optional, your call)

- Untracked ronanwrites `.mdx` drafts in `../kr-company-registry/docs/ronanwrites/` and
  `../kr-derivatives/docs/ronanwrites/` — content drafts; commit to those repos or move to
  the ronanwrites site as you prefer.
- `.claude/settings.local.json` is untracked (and not gitignored) in `kr-company-registry`,
  `kr-derivatives`, `jfia-forensic`, `kr-enforcement-cases` — harmless local state; gitignore
  it per-repo if you want fully clean working trees.
