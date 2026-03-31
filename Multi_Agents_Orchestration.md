# Multi-Agent Orchestration — Core Mental Models

This document extracts the tacit knowledge behind Anthropic's production multi-agent
system, derived from three internal source files: `coordinatorMode.ts` (370 lines),
`AgentTool/prompt.ts` (288 lines), and `forkSubagent.ts` (211 lines). These are not
theoretical guidelines — they are patterns crystallized from production experience and
encoded directly into the system's architecture.

The forensic-accounting-toolkit agent team (deployed 2026-03-31) was built on these
principles. Concrete examples below reference that implementation.

---

## Mental Model #1 — The Coordinator Understands; Workers Execute

**Never delegate understanding.**

The coordinator's single most important responsibility is *synthesis*. When a worker
returns results, the coordinator reads them, comprehends them, and then — and only
then — instructs the next worker with specifics: exact file paths, line numbers, what
to change and why. The coordinator is never a pass-through node.

> **Key insight:** The anti-pattern is explicit: "based on your findings, fix the bug"
> or "based on the research, implement it." These phrases outsource understanding to
> the worker. The moment the coordinator delegates understanding, the whole system's
> quality collapses.

**Wrong:**
```
"The convention audit found issues in kr-beneish. Please fix them."
```

**Right:**
```
"kr-beneish/pyproject.toml line 3: the [build-system] requires list contains
'setuptools' but must be ['hatchling']. Replace line 3 with:
requires = ['hatchling']
This was introduced after the 2026-03 restructure."
```

The difference is not style — it is whether the coordinator did the synthesis work
or handed it off.

---

## Mental Model #2 — Each Agent Is a Smart Colleague Who Just Walked In

Every agent lives in an isolated context window. The prompt is their entire world —
they have not seen the conversation, do not know what has been tried, and do not
understand why the task matters. Brief them like a new hire on their first day: explain
what you are trying to accomplish, what is already known, and provide enough surrounding
context for them to make judgment calls.

> **Key insight:** Two types of tasks require different prompts. For *lookups* (the
> answer is deterministic), give the exact command. For *investigations* (the answer
> is open), give the question — not a prescribed procedure. A procedure becomes dead
> weight the moment its premise is wrong.

**From the triage agent implementation:**
```
PURPOSE: Synthesize raw scan data into a ranked action list.
The human reads this every morning to decide what to work on.

WHAT YOU KNOW: [CONTEXT.md — full ecosystem map, 13 repos, conventions, data flow]

WHAT YOU HAVE: Output of triage-scan.sh, which scanned 13 sources.

JUDGMENT CALLS YOU MAY NEED TO MAKE:
- If multiple repos fail tests, prioritize by upstream dependency order.
  A kr-forensic-core failure cascades to all 5 platform repos.
- Board items marked AI-owned but requiring SEIBRO API are actually
  human-blocked. Flag them as needs-human.
```

This is a briefing, not a command.

---

## Mental Model #3 — Coordinator Mode vs. Fork Mode

There are two fundamentally different orchestration models, and they are mutually
exclusive.

**Coordinator mode:** The coordinator dispatches workers using an Agent tool, receives
their results as internal signals, and remains the only entity that speaks to the user.
The coordinator never executes tools directly — it only reads, thinks, and delegates.
Workers are the hands. The coordinator is the brain.

**Fork mode:** A parent agent copies itself. Each child inherits the parent's full
conversation context and system prompt. Because all children share byte-identical API
request prefixes, the prompt cache is maximized — forks are cheaper per token than
spawning fresh agents. Forks are appropriate when many parallel workers need the same
base context and their directives are the only thing that differs.

**Teammate mode:** The agent runs in a separate terminal pane (tmux or iTerm split).
Communication is file-based: the parent writes a task file to a mailbox path; the
teammate reads it, executes, and writes results back. No shared process tree. Best
for long-running background workers that need to run while the user continues working
in the main session. Cost: separate context window, no cache sharing with the parent.

**Worktree mode:** Each agent receives its own git worktree — an independent working
copy on a separate branch. Agents can edit files concurrently without conflict.
Isolation is at the filesystem and git level, not just the context level. Use this
when multiple implementation workers need to touch the same codebase simultaneously.
The results merge back when each worker's branch is complete.

| Mode | Process | Cache sharing | Best for |
|------|---------|--------------|---------|
| Fork | Child of parent | Yes — byte-identical prefix | Parallel tasks with shared context |
| Teammate | Separate, file mailbox | No | Long-running background workers |
| Worktree | Separate, isolated branch | No | Concurrent implementation on same codebase |

> **Key insight:** The forensic-accounting-toolkit orchestrator is a pure coordinator.
> The `orchestrator_agent.py` script only uses `Read` and `Bash` (for `gh` CLI) —
> it reads scratchpad files and creates GitHub issues. It never directly runs `pytest`,
> edits files, or touches repos. That is strictly for dispatched workers.

---

## Mental Model #4 — Context Overlap Determines Continue vs. Spawn

When a worker finishes one task and you need to run another, you have two options: send
a follow-up message to the same session (Continue), or start a fresh agent (Spawn).
The right choice depends on one question: how much of the worker's accumulated context
is relevant to the next task?

| Use **Continue** when | Use **Spawn** when |
|-----------------------|-------------------|
| The worker has error context you need (failed task) | The worker explored broadly but the next task is narrow — don't carry the exploration noise |
| You are building directly on its last output | You need independent verification (implementer's assumptions contaminate self-review) |
| The worker already understands the file structure | The first attempt was fundamentally wrong — stale context poisons the retry |

> **Key insight:** There is no universal default. This is a judgment call each time.

The `_sdk_helpers.py` implementation uses `ClaudeSDKClient` (stateful session) for
the retry path: when a worker fails, it sends a correction message to the *same* session
rather than spawning a new one. The worker already has the error — that is valuable.
Only after two failures does it escalate.

---

## Mental Model #5 — Verification Means Proving It Works, Not Confirming It Exists

A verifier that rubber-stamps weak work is worse than no verifier — it provides false
confidence. The verifier must be skeptical, independent, and test behavior rather than
presence.

> **Key insight:** Always spawn a *fresh* agent for verification. The agent that
> implemented something carries the implementer's assumptions — it will unconsciously
> verify what it believed it built, not what is actually there.

**From `data_validate_agent.py` — proving correctness, not existence:**

```python
# WRONG (existence check):
assert path.exists(), "file missing"

# RIGHT (correctness proof):
df = pd.read_parquet(path)
assert len(df) > 0, "EMPTY dataframe"
assert df['corp_code'].nunique() > 100, "suspiciously few companies"
assert df.isnull().mean().max() < 0.3, "null rate too high"
assert (df['close'] > 0).mean() > 0.9, "prices mostly zero"
```

The second block proves the pipeline produced *meaningful* data for the Korean
market — not just a non-empty file.

---

## Mental Model #6 — Parallelism Is Your Superpower

The coordinator can dispatch multiple workers simultaneously. One message with multiple
tool-use blocks triggers parallel execution at the API level.

The concurrency rule is simple:
- **Read-only tasks (research):** run freely in parallel
- **Write tasks (implementation):** one per file set — parallel writes conflict
- **Verification:** can run alongside implementation on *different* file areas

> **Key insight:** Sequential execution is the default failure mode of naive
> orchestration. The coordinator must actively choose parallelism wherever there is no
> dependency.

**From the tier1-tests.yml run on 2026-03-31:**
```
22:00 UTC — 11 repos launched simultaneously (matrix strategy)
22:00:09 — kr-enforcement-cases ✓ (12s)
22:00:09 — kr-forensic-core ✓ (9s)
22:00:10 — kr-company-registry ✓ (17s)
... all 11 complete within 20 seconds, in parallel
```

Sequential execution of 11 repos would have taken ~180 seconds. Parallel: 20 seconds.

---

## Mental Model #7 — Prompt Cache Is an Architecture Decision

Cost is not an afterthought — it shapes the architecture itself. The Anthropic API
caches prompts when the byte-prefix of consecutive requests is identical. Cache misses
multiply API cost; cache hits make agents economically viable at scale.

The pattern that maximizes cache hits:

```
[LARGE STATIC PREFIX — identical for every agent]
  ecosystem description, repo list, conventions, hard rules, escalation triggers
  → this is CONTEXT.md, loaded verbatim by every agent script

[SMALL DYNAMIC SUFFIX — differs per task]
  today's specific instruction, which files to check, what was found in scan output
```

> **Key insight:** Even a single character difference in the static prefix breaks the
> cache for the entire prefix. This is why dynamic data (timestamps, run IDs) must
> *never* appear in system prompts — only in the user-turn prompt.

In the forensic toolkit, `CONTEXT.md` (~2,000 tokens) is loaded verbatim by all four
agent scripts. Only `TASK_PROMPT` (~200-500 tokens) varies. When the triage agent and
convention audit agent both call the API within the same billing period, the shared
prefix is a guaranteed cache hit.

The same principle is why Anthropic's fork implementation passes the *already-rendered*
parent system prompt to children rather than regenerating it — even a GrowthBook
feature flag toggling between cold and warm state produces a different byte string,
which breaks the cache.

---

## Mental Model #8 — Worker Results Are Internal Signals, Not Conversation Partners

The coordinator has one communication channel for the user (GitHub issues, summary
posts) and a separate internal channel for receiving worker results (scratchpad files,
task notifications). These must never be confused.

> **Key insight:** Never thank workers. Never acknowledge their output in the user-facing
> channel. Worker results arrive as internal signals. The coordinator processes them
> silently and speaks only to the user.

**From the orchestrator design:**

When `orchestrator_agent.py` reads `test-results.json` and finds that
`kr-derivatives` failed, it does not emit "The test runner reported a failure in
kr-derivatives." It silently cross-references that with `triage.json` and
`data-validation.json`, synthesizes the root cause, and creates a GitHub issue with
a specific brief — a message addressed to the *human*, not to the test runner.

---

## Mental Model #9 — Never Predict Results You Don't Have

When a worker is running, you know nothing about its output. Do not fabricate or hint
at what it might find. Do not say "the test results will probably show X." The only
honest response while a worker runs is: "It is still running — results coming."

> **Key insight:** Fabricated intermediate results are the most dangerous failure mode
> in autonomous agents. They create false confidence that cascades through the system.
> The orchestrator's integrity depends entirely on reporting only what has actually
> been observed.

---

## Mental Model #10 — The File System Is the Shared Memory

Agents cannot call each other. There is no direct message passing between worker
processes. The canonical communication mechanism is the file system: workers write
results to known paths; other agents read from those paths.

This is the most primitive form of IPC (inter-process communication), and also the
most robust — it works across sessions, across time, and survives individual agent
failures without data loss.

> **Key insight:** A shared "scratchpad" directory with predictable filenames per
> worker is the standard pattern. Structure files however fits the work.

**From the forensic toolkit deployment:**

```
$GITHUB_WORKSPACE/_scratchpad/
  test-results.json       ← written by tier1-tests
  triage.json             ← written by tier2-triage
  convention-audit.json   ← written by tier3-convention-audit
  doc-drift.json          ← written by tier1-doc-drift
  count-sync.json         ← written by tier1-count-sync
  orchestrator.json       ← written by orchestrator (synthesis of all above)
  escalation.md           ← written by any agent hitting a hard stop
```

The orchestrator reads all seven files before synthesizing. Each file is produced
independently, at different frequencies, by different agents. The scratchpad is the
single shared state of the system.

---

## Mental Model #11 — Research → Synthesis → Implementation → Verification

This four-phase structure applies to nearly every complex task:

1. **Research:** Workers explore in parallel. Read-only. Maximum parallelism.
2. **Synthesis:** The coordinator alone reads all research outputs and produces a
   coherent understanding with specific implementation specs. This step belongs
   exclusively to the coordinator and cannot be delegated.
3. **Implementation:** Workers execute the coordinator's specs. Serial per file set.
4. **Verification:** A *fresh* worker confirms the implementation produced correct
   results. Never reuse the implementation agent for this step.

> **Key insight:** Synthesis is the coordinator's monopoly. If the coordinator skips
> synthesis and passes research outputs directly to an implementation worker, the
> system degrades — the implementation worker now has to do two jobs simultaneously
> and will do both worse.

**How the forensic toolkit orchestrator follows this each run:**

1. **Research:** Download all 7 scratchpad artifacts from worker workflows (parallel).
2. **Synthesis:** `orchestrator_agent.py` cross-references them — "kr-derivatives
   tests fail AND data is 23 days old → data staleness is root cause, not code."
3. **Implementation:** Creates GitHub issue with specific brief (the "dispatch" step).
4. **Verification:** Checks GitHub issue state from *previous* orchestrator run —
   were those briefs acted on? How many are still open?

---

## Mental Model #12 — Continue Failed Workers; They Have Error Context

When a worker fails, do not discard it and spawn a replacement. The failed worker
already has the full error context inside its session. Send a correction message
explaining what went wrong and ask for a different approach. This is almost always
more efficient than restarting cold.

Only escalate to a human when the correction also fails — three consecutive failures
at the same task is the escalation threshold.

> **Key insight:** Spawning fresh on failure is the intuitive response but the wrong
> one. The new agent starts with no error context and will likely reproduce the same
> failure.

**From `_sdk_helpers.py`:**
```python
async with ClaudeSDKClient(options=options) as client:
    try:
        await client.query(task_prompt)
        # ... collect response
    except AgentError as e:
        # Worker failed — continue same session with error context (Principle #12)
        await client.query(
            f"Your previous attempt failed: {e}\n"
            f"The error context you already have is valuable — do not start over.\n"
            f"Try a different approach."
        )
        # ... if this also fails → write escalation.md → raise
```

---

## Mental Model #13 — CLAUDE.md Is a Live Control Plane, Not an Init File

The framework re-reads the CLAUDE.md hierarchy on *every turn*, not once at session
start. This is not a performance detail — it is an architectural consequence with
practical implications.

The four-tier hierarchy (resolved in order):

1. `~/.claude/CLAUDE.md` — global rules, applies to all projects
2. `./CLAUDE.md` — project-level rules, checked into the repo
3. `.claude/rules/*.md` — module-level rules, scoped to specific areas
4. `CLAUDE.local.md` — local override, not committed (gitignored)

Total capacity: ~40,000 characters across all tiers. Most projects use less than 1%.

> **Key insight:** The connection to Mental Model #7 is direct. `CONTEXT.md` is loaded
> explicitly in code (`Path("scripts/agents/CONTEXT.md").read_text()`). CLAUDE.md tiers
> are loaded by the framework itself. If your static context fits in the project-level
> CLAUDE.md, the framework handles the loading on every turn — you do not need to wire
> it in every agent script. The two mechanisms are equivalent for caching purposes;
> CLAUDE.md simply delegates the loading responsibility upward.

The per-turn re-reading also means mid-session configuration changes take effect
immediately on the next message. If you update CLAUDE.md during a long orchestration
run, the change is live — there is no need to restart the session.

---

## Mental Model #14 — Design for Interruptibility, Not Just Completion

The full pipeline is implemented as an async generator. When you press Escape, only
the current generation stream is cancelled. The agent's context window, its accumulated
tool results, and all prior conversation turns remain intact. The interrupt is a clean
boundary, not a state reset.

This has a non-obvious implication for orchestration design: **partial completion is
recoverable**. A coordinator that has dispatched three workers and received two results
does not need to restart from scratch if the third is interrupted. It can resume from
exactly the state after the second result.

> **Key insight:** The corollary for orchestration design: break long pipelines into
> explicit phases with observable intermediate state (Mental Model #10 — scratchpad).
> An interrupted pipeline can always be resumed from its last committed scratchpad
> output. A pipeline that holds all state in-memory loses everything on interrupt.

---

## Operational Notes — Context and Session Management

These are not orchestration principles but are underused capabilities that directly
affect long-running agent systems.

**Use `/compact` as a manual save, not a last resort.**

Five compression strategies run automatically: microcompact (prunes old tool results),
context collapse (summarises a conversation window), session memory extraction (saves
key context to file), full compact (entire history summary), and PTL truncation (drops
oldest message groups). The system applies these when approaching the context limit.

The problem with waiting: automatic compression prioritises by recency and perceived
importance — which may not match what *you* need to preserve. Trigger `/compact`
deliberately before context-critical transitions (e.g., before starting a new phase
of a long implementation, or before the verification step that needs specific earlier
context). Think of it as a manual save point in a long game, not an emergency measure.

**Use `--fork-session` to branch from a past conversation state.**

Every session is stored as JSONL. Three flags:
- `--continue`: resume the most recent session
- `--resume <id>`: resume a specific session by ID
- `--fork-session <id>`: create a new branch from a specific point in a past session

`--fork-session` is the underused one. If an orchestration run took a wrong direction
at step 4 of 10, you do not need to rerun steps 1-3. Fork from the step-3 checkpoint
and take the alternate path. This is equivalent to a git branch — the original session
is preserved unchanged.

---

## Summary Checklist

Before designing or extending any multi-agent system, verify:

- [ ] The coordinator synthesizes every worker result before acting — never passes through
- [ ] Every agent prompt is a full briefing: goal, context, known constraints, judgment guidance
- [ ] Context overlap was evaluated before choosing Continue vs. Spawn
- [ ] Verification uses a fresh agent, separate from the implementer
- [ ] Read tasks are parallelized; write tasks are serial per file set
- [ ] The system prompt is split: large static prefix + small dynamic suffix
- [ ] Worker results are internal signals; only outputs addressed to the user are external
- [ ] No intermediate result is reported until it is actually observed
- [ ] All inter-agent communication goes through predictable file paths (scratchpad)
- [ ] Every complex task follows: Research → Synthesis (coordinator only) → Implementation → Verification
- [ ] Failed workers are continued, not replaced
- [ ] Hard escalation triggers are written into every agent's system prompt
- [ ] Execution model is chosen explicitly: fork (cache-sharing), teammate (background), or worktree (concurrent edits)
- [ ] CLAUDE.md tiers are used for static context where possible — the framework loads them every turn without code wiring
- [ ] Long pipelines store intermediate state to scratchpad so they can be resumed after an interrupt
- [ ] `/compact` is triggered before context-critical phase transitions, not only when the window is full

---

*Source: Anthropic internal production code — coordinatorMode.ts, AgentTool/prompt.ts, forkSubagent.ts*
*Additional source: analysis of leaked Claude Code source (~510k lines), via unclejobs.ai thread, 2026-03-31*
*Applied: forensic-accounting-toolkit agent team deployment, 2026-03-31*
