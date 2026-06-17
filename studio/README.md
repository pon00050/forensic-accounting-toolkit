# Forensic Studio — a self-running, internal-only AI operations layer

The Studio keeps the 13-repo forensic-accounting ecosystem **demonstrably alive and lightly
self-maintaining** with **minimal/zero routine human intervention**, inside a hard **cage** that
makes the documented autonomous-agent failure modes structurally impossible. Design rationale and
the adversarial review are in `../AGENT_TEAM_REDESIGN.md`; resume context in `../RESUMING.md`.

> **Honest status (2026-06-17):** the CAGE is fully built and the maintenance loop does one REAL
> deterministic job (doc-count reconciliation). The heavyweight ENGINES — full DART data refresh and
> the LLM fix→verify→merge crew — are **scaffolded but not yet implemented** (see "The loops"). Today
> the Studio keeps the repo alive and fixes doc-count drift; it does **not** yet refresh parquets or
> auto-fix code.

## Posture: internal-only
Outputs are committed as **reproducible, provenance-stamped, machine-generated/unreviewed** artifacts.
The Studio does **not** publish entity-level forensic conclusions — outputs stay "probability, not a
verdict" (the project's own hard rule). This removes the defamation / unreviewed-claim risk surface.

## The cage (control plane) — fully built
- `fleet.config.yml` — reference + partial runtime config. `posture` + `auto_merge_classes` are read by
  `discover.py`; the rest (schedules, caps, models, dead-man window) are reference copies whose
  authoritative homes are noted in the file header (not yet read by the loops).
- `FLEET_ENABLED` (GitHub repo **variable**) — the live master switch (currently **on**). Every loop runs
  the heartbeat gate first (`.github/actions/studio-heartbeat`); if the switch is off or the
  dead-man's-switch check-in is stale, the loop is a **green no-op skip** (fail-closed, no email).
- `guardrails/` — `check_domain_rules.py` (CI gate: `data/raw/` is immutable) and `pre_data_raw_guard.py`
  (Claude Code PreToolUse hook blocking writes to `data/raw/`). Both tested.
- `provenance.py` — stamps every artifact with model, date, git sha, input hashes, disclaimer.
- `run-log.md` — append-only log of every run.
- `state/LAST_CHECKIN` — dead-man's-switch timestamp; **auto-bumped on each successful enabled run**, so
  while the fleet runs it stays alive and the repo stays active (GitHub won't auto-disable the schedules).

## The loops
- **`studio-maintain`** (weekly) — DETERMINISTIC, real: `discover.py` writes the backlog work-queue from
  `maintenance/backlog.yml`, and `sync_doc_counts.py` reconciles ECOSYSTEM.md's `N tests` figures to the
  authoritative hub CLAUDE.md, committing the fix. `mode=full` would run the LLM crew
  (`scripts/agents/fix_agent.py` → `verify_agent.py`, auto-merge SAFE classes only) — **Phase 3, not yet
  built**; the execute step is a no-op even with `ANTHROPIC_API_KEY` set.
- **`studio-refresh`** (weekly) — `smoke` = plumbing/liveness check (commits a dated status note). `full`
  (needs `DART_API_KEY`) calls `studio/loops/refresh.sh`, which currently only *imports* kr-dart-pipeline
  — **the actual DART extraction is a Phase-2 scaffold**, so it does not refresh parquets yet. Intended:
  DART-only ETL via the FinanceDataReader backend (avoids the pykrx cloud geo-block).

## Operating it (the only human touchpoints)
1. **Pause anytime:** `gh variable set FLEET_ENABLED --body false` → loops become green no-op skips.
   (Paused >~60 days → GitHub auto-disables the schedules; resume with `gh workflow enable` on both
   studio workflows + `FLEET_ENABLED=true`.)
2. **Finish the engines (to make it truly deliver):** implement `loops/refresh.sh`'s ETL body and the
   studio-maintain `full` execute step, then add `DART_API_KEY` / `ANTHROPIC_API_KEY` (or a
   `CLAUDE_CODE_OAUTH_TOKEN`) and set the Anthropic workspace ceiling.

Cost: deterministic loops are **$0** (free public-repo CI + free DART API). The LLM crew (once built)
spends ~$0.7–0.9/fix task; ~$5–20/mo active, tapering. See `../AGENT_TEAM_REDESIGN.md` §cost.
