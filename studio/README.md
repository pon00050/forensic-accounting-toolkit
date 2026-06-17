# Forensic Studio — a self-running, internal-only AI operations layer

The Studio keeps the 13-repo forensic-accounting ecosystem **alive and improving** with
**minimal/zero routine human intervention**, inside a hard **cage** that makes the
documented autonomous-agent failure modes structurally impossible. Design rationale and
the adversarial review are in `../AGENT_TEAM_REDESIGN.md`; resume context in `../RESUMING.md`.

## Posture: internal-only
It refreshes data and runs the maintenance crew, committing **reproducible, provenance-stamped
artifacts**. It does **not** publish entity-level forensic conclusions — outputs stay
"probability, not a verdict" (the project's own hard rule). This removes the defamation /
unreviewed-claim risk surface.

## The cage (control plane)
- `fleet.config.yml` — single source of truth: model routing, per-run caps, monthly ceiling, schedules.
- `FLEET_ENABLED` (GitHub repo **variable**) — the master switch. **Default off.** Every loop runs
  the heartbeat gate first (`.github/actions/studio-heartbeat`); if the switch is off or the
  dead-man's-switch check-in is stale, the loop is a **green no-op skip** (fail-closed, no email).
- `guardrails/` — `check_domain_rules.py` (CI: `data/raw/` is immutable, runs on every change) and
  `pre_data_raw_guard.py` (a Claude Code PreToolUse hook blocking writes to `data/raw/`).
- `provenance.py` — stamps every artifact with model, date, git sha, input hashes, and a
  machine-generated/unreviewed disclaimer.
- `run-log.md` — append-only log of every run (what ran, result).
- `state/LAST_CHECKIN` — the dead-man's-switch timestamp.

## The loops
- **`studio-refresh`** (`.github/workflows/studio-refresh.yml`) — weekly. `smoke` = plumbing check
  (no secrets); `full` = real DART ETL via `studio/loops/refresh.sh` (deterministic, no LLM,
  FinanceDataReader backend to avoid the pykrx cloud geo-block).
- **`studio-maintain`** (`.github/workflows/studio-maintain.yml`) — weekly. `discover.py` produces the
  work queue from `maintenance/backlog.yml` (deterministic). `full` execution reuses the existing
  `scripts/agents/{fix_agent,verify_agent}.py` two-agent gate (one item → one PR → fresh verify →
  auto-merge only on green for SAFE classes); wired in Phase 3.

## Operating it (the only human touchpoints)
1. **Enable:** set the repo variable `FLEET_ENABLED=true` (`gh variable set FLEET_ENABLED --body true`).
2. **Pause anytime:** set it back to `false`. Loops immediately become green no-op skips.
3. **Check in:** update `state/LAST_CHECKIN` to today (any commit touching it). If no check-in within
   `deadman_checkin_max_days` (120), loops fail closed until you return.
4. **Go live (full mode):** add repo secrets `DART_API_KEY` (refresh) and `ANTHROPIC_API_KEY` *or*
   `CLAUDE_CODE_OAUTH_TOKEN` (maintenance), and set the Anthropic workspace monthly ceiling.

Cost: deterministic loops are **$0** (free public-repo CI + free DART API). Only the maintenance
crew spends tokens (~$0.7–0.9/fix task; ~$5–20/mo active, tapering). See `../AGENT_TEAM_REDESIGN.md` §cost.
