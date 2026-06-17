# Autonomous Refinement Team — Design Synthesis

> Written 2026-06-17. A design for how a team of AI agents could autonomously refine the
> 13-repo forensic-accounting ecosystem, unattended, after the owner steps away.
> Companion to `RESUMING.md` (resume guide) and `AGENT_ARCHITECTURE.md` (the *existing*,
> now-disabled system).
>
> **Build status (2026-06-17, post-audit):** PARTIALLY BUILT. The *cage* (heartbeat/fail-closed gate,
> `data/raw` guardrail + PreToolUse hook, provenance, run-log, FLEET_ENABLED master switch) is live, and
> the maintenance loop performs one *real* deterministic job (doc-count reconciliation). The heavyweight
> *engines* described below — full DART data refresh and the LLM fix→verify→merge crew — are **scaffolded
> but not yet implemented**. Treat this document as the design/target; see `studio/README.md` and
> `RESUMING.md` for exactly what runs today.

Grounded in four parallel research streams (2026-06-17): (A) reverse-engineering the existing
agent system, (B) cataloging the real refinement work surface across the 13 repos, (C) current
SOTA for autonomous multi-agent SWE, (D) cost/verification/safety for unattended fleets.

---

## 0. TL;DR

You already built an elaborate autonomous agent system (15 workflows, a 4-tier orchestrator, a
Cloudflare/Telegram control plane, a real fix→verify→PR loop). It was **disabled** because it ran
unattended with **no global budget cap, no "is anyone watching?" check, and a human-approval gate
on a scheduled job** that could only ever time out and fail.

The redesign is **not "add more agents."** Anthropic's own guidance is blunt: *coding tasks don't
parallelize within a task, and multi-agent systems burn ~15× the tokens.* The win is a **leaner,
cost-bounded, self-throttling system** where parallelism comes from **many single agents working
different repos at once** — coordinated through a **GitHub Issues work-queue**, each producing
**one repo → one branch → one PR**, every PR **hard-gated on a fresh independent verifier + green
CI**, and the whole fleet **caged inside its own API workspace with a hard monthly dollar cap**.

There is enough genuinely valuable, agent-safe work to justify it: **test depth, type/doc coverage,
lint config, and doc-count sync** across ~25k LOC of currently thinly-tested analytical code.

**Verdict: worth building — but as a deliberately small, caged "maintenance crew," not the
ambitious autonomous org the old docs imagined.**

---

## 1. Reframe: you already built one (and why it broke)

The existing system (see `AGENT_ARCHITECTURE.md`, now disabled) is a 4-tier pipeline:

- **Tier 1 (bash, no LLM):** deterministic scanners — cross-repo tests, doc-drift, count-sync, convention quick-check, sibling-CI monitor. Cheap, good.
- **Tier 2 (Haiku):** triage synthesis + data validation → structured JSON.
- **Tier 3 (Sonnet, weekly):** convention audit, pipeline ETL run, JFIA enrichment.
- **Orchestrator (Sonnet):** consumes all scratchpads, emits action briefs, dispatches fixes.
- **Tier 4 (Sonnet, event-driven):** the real engine — `fix_agent` edits → **fresh `verify_agent` re-runs the suite independently** → PR only if verify passes → auto-merge low-risk categories.
- **Control plane:** Cloudflare Worker + Telegram bot as a "team leader on your phone," with KV memory and an AI-Gateway proxy.

**What's genuinely good and must be kept:**
1. **The two-agent fix→verify gate.** The verifier is a *fresh context* with no knowledge of the fix and only Bash+Read; the PR is hard-blocked unless it re-passes the full suite. This is the strongest idea in the whole system.
2. **File-based scratchpad IPC** + orchestrator-as-pure-consumer (zero tools, everything pre-injected).
3. **Per-agent policy bundles** with `max_budget_usd`/`max_turns` on every call, and **model routing** (Haiku classify / Sonnet synthesize / never Opus on autonomous paths).
4. **Deterministic, no-LLM autofixes** (count-sync, doc-drift) with `[skip ci]` to avoid push loops.
5. **Dedup guards** everywhere (skip-if-open-PR / skip-if-open-issue / single summary issue).
6. **The `Owner: AI/Human` board taxonomy** — a clean separation of autonomously-actionable vs human-blocked work.

**Why it failed as an *unattended* system (the four root causes the redesign must fix):**
1. **Human-approval gate on a scheduled job.** `tier3-pipeline` ran weekly, hit the `production`
   environment's required-reviewer gate, waited ~30 days, and **failed on timeout every cycle.**
   A job is either unattended (no human gate) or interactive (no schedule) — never both.
2. **No global cost governor.** Per-call caps existed ($0.30–$5), but **nothing capped daily/monthly
   spend** or paused schedules when output went unread. Daily triage + tests + fix fan-out billed
   Anthropic every day with nobody reading the results.
3. **No "is anyone watching?" liveness check.** Schedules ran identically whether you engaged daily
   or vanished for two months.
4. **The "agent team" was mostly aspirational.** `Multi_Agents_Orchestration.md` describes coordinator
   mode, fork/teammate/worktree, event buses — but the shipped reality is a pipeline of independent
   one-shot scripts. There is no coordinating team yet; there's a cron-driven script collection.

Other gaps: silent PAT degradation (sibling pushes/board-sync fail invisibly when `ECOSYSTEM_PAT` is
missing/under-scoped); no issue state machine (work re-diagnosed across runs via title regex); no
downstream-dependent regression guard on auto-merge (a foundation-lib change auto-merges on its own
tests, never re-running krff-shell which imports everything); no flake handling (a transient red
triggers a full Sonnet fix attempt); no aggregated observability of agent cost/output.

---

## 2. Is it worth it? The actual work surface

Research stream (B) audited all 13 repos. **These are clean codebases** — near-zero marker debt
(8 deliberate `NotImplementedError` SEIBRO/Phase-2 deferrals, a couple of TODOs), and **zero
`@pytest.mark.skip`/`xfail` anywhere.** The imperfection is real but lives in coverage and structure,
not broken logic — the ideal profile for autonomous agents. The work, by autonomy-safety:

**SAFE (mechanical, test-verifiable — the agent team's bread and butter):**
- **Test depth.** The biggest opportunity. `kr-stat-tests` has **5 tests over 3,413 LOC** (it checks
  that files *exist* — not one assertion exercises the PCA/bootstrap/LASSO/RF math). `kr-dart-pipeline`
  has **zero tests for its 15 extractors or 684-line transform.py**. `kr-enforcement-cases` documents
  "65 tests for 19 modules — deferred, fixture parquets needed." The shared blocker across three
  repos is **"need fixture parquets"** — building small synthetic golden-input fixtures is mechanical
  and unlocks all three.
- **Type-hint & docstring coverage.** `kr-forensic-core` — the zero-dependency package *everyone*
  imports — has **9% return-type-hint coverage and 18% docstrings.** It should be the best-documented,
  not the worst. Mechanical sweep, test-verified.
- **Lint/type config.** Only 4 of 12 repos configure ruff; no repo has mypy wired ecosystem-wide.
  Add a consistent `[tool.ruff]`/`[tool.mypy]` block + `ruff check --fix`.
- **Doc-count sync.** `kr-enforcement-cases` README says `violations.csv` = 240 rows; it's actually
  **6,235** (still needs fixing). ECOSYSTEM.md's kr-beneish count drift (was 61, should be 73) is
  now **auto-reconciled by the Studio's `sync_doc_counts.py`** — fixed automatically on 2026-06-17.

**NEEDS REVIEW (agent drafts, human signs off):**
- **krff-shell monolith de-duplication.** `02_Pipeline/` + `03_Analysis/` hold ~9,700 LOC of copies
  of kr-dart-pipeline / kr-anomaly-scoring that **have already diverged** from canonical sources.
  Highest correctness risk in the ecosystem (two ETL copies that disagree) — but removing them needs
  the documented test refactor + architectural sign-off.
- Pagination logic (>100-filing CB case), logic-bearing refactors, golden-value choices for
  statistically-loaded tests.

**HUMAN-ONLY (domain-correctness / external):**
- SEIBRO/XB-002 (external API + credential decision — April ETA has passed; re-check first).
- Phase-3 DART sub-document parser scope; the 53.6% sigma-fallback methodology in kr-derivatives.
- Anything touching the four hard rules (GAAP/IFRS, split-adjustment, M-score calibration, raw data).

**Top 4 highest-value / lowest-risk, in order:** (1) synthetic fixture parquets + behavioral tests
for kr-stat-tests / kr-dart-pipeline / kr-enforcement-cases; (2) type-hint + docstring sweep starting
with kr-forensic-core; (3) ecosystem-wide ruff/mypy; (4) doc-count sync.

---

## 3. Target architecture

The shape, end to end:

```
            ┌─────────────────────────────────────────────────────────────┐
            │  HEARTBEAT GATE  — is the fleet enabled? under budget? not    │
            │  paused?  (checks a pause flag + month-to-date spend first)   │
            └─────────────────────────────────────────────────────────────┘
                                   │ (proceed only if all green)
                                   ▼
   DISCOVERY (weekly, cheap)   ┌────────────────┐   files labeled GitHub Issues
   Opus planner scans 13 repos │  orchestrator  │──►  agent:test-gap / agent:lint /
   for coverage/lint/doc debt  └────────────────┘     agent:docs / agent:typehints
                                                              │  (the WORK QUEUE)
                                   ┌──────────────────────────┘
                                   ▼  one issue ⇒ one run ⇒ one repo ⇒ one branch
   EXECUTION (per issue)  ┌────────────────┐   claim issue → plan → edit → run tests
   Sonnet (Haiku trivial) │  fix executor  │   in clean checkout → open PR → stop
                          └────────────────┘
                                   │
                                   ▼
   VERIFICATION (the gate)  ┌────────────────┐  Gate 0 mechanical (lint/types/tests/
   fresh-context critic     │   verify gate  │  DOMAIN CHECKS) → 1 diff-scope → 2 CI
   (Opus, Bash+Read only)   └────────────────┘  green → 3 Opus critic → 4 golden evals
                                   │
                  ┌────────────────┴───────────────────┐
                  ▼ auto-merge whitelist                ▼ everything else
        docs/tests/lint/counts             →  PROPOSE-DON'T-MERGE: PR waits in queue
        (Gates 0–2 + 4 green) → squash-merge   async human review; TIMEOUT → ABANDON
```

**Three design rules that follow from the SOTA research:**
1. **Parallelism is across repos, not within a task.** Many single agents run at once, each owning
   one repo/issue/PR. This sidesteps the 15× multi-agent token tax (Anthropic: "coding tasks don't
   parallelize well") while still getting throughput.
2. **GitHub Issues *are* the blackboard.** Durable, dedup-able (claim by assignment/label), auditable,
   human-reviewable for free. The orchestrator *files issues*; it never edits code directly.
3. **One agent → one repo → one branch → one PR.** Atomic, reviewable, and the merge story stays sane.
   Use git worktrees if running several locally at once so conflicts surface at merge, not silently.

**Runtime (pick one — both far leaner than the old 15-workflow stack):**
- **`anthropics/claude-code-action@v1`** on a `schedule:` cron. Runs on your GitHub runners, can
  create PRs/commits/reviews, scoped by the GitHub App. Lowest friction; you already use Actions.
- **Claude Code Routines** (managed cloud, GA April 2026). Runs full Claude Code sessions on
  Anthropic's infra with scheduled / API / GitHub-event triggers and *no approval prompts* — purpose-built
  for unattended ops (their named use cases: backlog maintenance, alert triage, code review, docs-drift).

**Framework verdict:** **stay lean — Claude Agent SDK + claude-code-action only.** Skip
LangGraph/CrewAI/AutoGen/OpenAI-SDK/Devin: they add orchestration machinery that duplicates what
GitHub Issues + the SDK's subagents already give you, at the cost of more code for one absent owner
to maintain.

---

## 4. The control plane (non-negotiable for unattended operation)

This is the layer the old system lacked. It is what makes "leave it running for months" safe.

### 4.1 Cost — four independent caps (defense in depth)
| Layer | Mechanism | Starting value |
|---|---|---|
| Org backstop | Anthropic monthly spend limit (429 on hit) | tier ceiling — the wall you never reach |
| **Fleet isolation** | **Dedicated API workspace + key, own spend cap** | **~$50/mo — a runaway can't touch your wallet or interactive usage** |
| Per-run hard stop | SDK `max_budget_usd` + `max_turns` (terminates with `error_max_budget_usd`) | $0.50–$2 / 20–40 turns per task |
| Model routing | Haiku classify · Sonnet execute · Opus *only* planner + verify-judge | per-subagent `model` + `effort` |
| Input cost | Prompt caching (frozen prefix of shared CLAUDE.md/conventions) + Batch API (50% off) for bulk reclass | verify `cache_read > 0` |
| Loop guard | bounded retries (max 2) → **escalate, never loop** | + `PreToolUse` hook caps test-suite invocations |

### 4.2 Verification — a cheap→expensive ladder (block early, pay late)
| Gate | Cost | Catches | Block? |
|---|---|---|---|
| 0 Mechanical: lint/types/**tests**/**domain checks** | ~free | breakage, schema/domain violations | **Hard** |
| 1 Diff-scope: size limits, forbidden-path, **test-file edits** | ~free | scope creep, test-gaming | **Hard** |
| 2 CI green (the **trust anchor**) | CI min | integration breakage | **Hard** |
| 3 Opus critic — fresh context, rubric, ≠ author model | $$ | "plausible but wrong" logic | Soft → queue if uncertain |
| 4 Golden evals (frozen known forensic cases) | $ | domain regressions | **Hard** |
The LLM critic **augments, never replaces** deterministic gates (judges have position bias, are
config-sensitive, and miss "corrupt success"). Swap-test it for bias; spot-check ~10% of verdicts.

### 4.3 Non-blocking human-in-the-loop (the fix for the silent-stall death)
- **Propose-don't-merge** by default for anything outside the auto-merge whitelist. The PR queue *is*
  the interface; work accumulates safely without blocking the fleet.
- **Async batched review** (PR list + daily digest email), not synchronous approval prompts.
- **Every human gate has a timeout → ABANDON (never proceed) + an out-of-band alert.** The old
  system's fatal flaw was a gate that stalled *silently*; here a missed gate notifies and marks the
  item failed-needs-attention, visibly.
- **A global pause flag** (sentinel file / workspace key-disable) the scheduler checks before every run.
- **Tiered by reversibility:** auto-merge (docs/tests/lint/counts) · propose-and-queue (logic/refactor) ·
  confirm-before-act (force-push, `data/raw/` writes, spend, deleting published artifacts — never on
  the autonomous path).

### 4.4 Domain guardrails as code — the part unique to forensic accounting
Encode the four hard rules as **deterministic CI checks + a `PreToolUse` hook — NOT prompt
instructions.** (Reward-hacking research shows models rationalize around advisory prose but cannot
bypass a check that runs in the harness and is tripped by their own diff.)
| Hard rule | Enforced as |
|---|---|
| Never mix K-GAAP / K-IFRS | CI test: any record feeding a ratio carries `accounting_standard`; joins assert a single standard. Golden eval: a mixed input that *must* raise. |
| Split-adjust before price ratios | Price-ratio path requires an "adjusted" provenance flag; cross-check `kr-trading-calendar` split dates. Auto-trigger `/diagnose-moneyness` on any kr-derivatives edit yielding moneyness >10× and block until classified. |
| No M-score extrapolation; probability not verdict | `kr-beneish` test: out-of-calibration inputs return a flagged/`INCONCLUSIVE` result, never an extrapolated number or boolean verdict. |
| `data/raw/` immutable | `PreToolUse` hook **rejects any Edit/Write/Bash targeting `data/raw/` before it executes** + read-only FS perms + CI diff check. The cleanest "agent cannot bypass" guardrail. |
Plus: **disable WebFetch/WebSearch for editing agents** (they edit code, not browse — closes the
indirect-prompt-injection vector; treat fetched DART data as untrusted *data*, never instructions),
keep credentials out of the fleet's reachable env (breaks the "lethal trifecta"), and run the
existing `/leak-audit` skill on every PR.

---

## 5. The work program (what the team actually does, sequenced)

A standing backlog the discovery orchestrator files as labeled issues, roughly in value order:

1. **Fixture-parquet + behavioral-test campaign** (`agent:test-gap`). Build small synthetic golden
   fixtures, then real assertions for kr-stat-tests (the 3,313 untested LOC of math), kr-dart-pipeline
   (15 extractors + transform.py), kr-enforcement-cases. *Human signs off on golden values for
   statistically-loaded cases; agents build the harness and mechanical cases.*
2. **kr-forensic-core type-hint + docstring sweep** (`agent:typehints`, `agent:docs`), then the rest
   of the ecosystem. Start with the foundation everyone imports.
3. **Ecosystem ruff + mypy rollout** (`agent:lint`). Add config, `ruff check --fix`, fix findings.
4. **Doc-count + cross-reference sync** (`agent:docs`). The 240→6,235 enforcement drift, ECOSYSTEM.md
   counts — this is what the existing `post-commit-test-sync.py` hook already wants to drive.
5. **(Gated) krff-shell monolith de-duplication** — drafted by an agent, **human-reviewed**, because
   it needs the test refactor + architectural call. The one high-value item that must not be unattended.

---

## 6. Phased rollout (crawl → walk → run)

- **Phase 0 — Cage first (before any agent runs).** Create the isolated API workspace + key + $50/mo
  cap; add the four domain guardrails as CI checks + the `data/raw/` `PreToolUse` hook; add the global
  pause flag + heartbeat gate; set up the daily spend/PR digest. *No agent work until the cage exists.*
- **Phase 1 — One safe loop, attended.** Enable a single task type (`agent:docs` count-sync — already
  deterministic, no LLM) end to end: discovery files an issue → executor → verify → auto-merge. Watch
  it for a week. This re-proves the loop you already built, now caged.
- **Phase 2 — Add the verify-gated LLM loop.** Turn on type-hints + lint with the full Gate 0–4 ladder
  and auto-merge whitelist. Still attended weekly.
- **Phase 3 — The test campaign + walk away.** Enable the fixture/test work (highest value), confirm
  the digest + pause flag give you control without attention, then let it run. Re-check monthly via
  the digest.

---

## 7. Honest caveats

- **This is a maintenance crew, not a product team.** It will raise coverage, tighten types, fix docs,
  and keep things green. It will **not** make domain-correctness judgments, design new analytics, or
  unblock SEIBRO. The highest-value *intellectual* work here stays human.
- **Diminishing returns.** Once the test/type/lint/doc debt is paid down (a few months of runs), the
  safe backlog thins out. Plan for the team to *wind down to near-idle*, not run forever — which is
  itself a feature (low standing cost).
- **The cost foot-gun is real.** The June 15 2026 API-billing change produced documented multi-thousand-dollar
  runaways. The workspace cap + per-run caps are what make "set and forget" safe; do not skip Phase 0.
- **The old docs lie.** `Multi_Agents_Orchestration.md` describes a richer system than was ever built.
  Treat code (`tier4-autofix.yml`, the `scripts/agents/*.py` POLICY blocks) as ground truth, the docs
  as aspiration.
- **You can also just… not.** Given you're switching gears, a legitimate option is to leave everything
  shelved (per `RESUMING.md`) and build this only if/when you return. Nothing here decays if unbuilt.

---

## 8. The minimal first step (if you do nothing else)

Build **Phase 0 + Phase 1** only: cage the fleet (isolated workspace + caps + the four guardrails +
pause flag + digest), then re-enable the *single* deterministic count-sync loop you already have.
That gives you a safe, observable, near-zero-cost proof that an unattended agent can do real work here
without the failures that shelved v1 — and it's the foundation everything else bolts onto.
