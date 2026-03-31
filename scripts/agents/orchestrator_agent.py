"""
orchestrator_agent.py — Sonnet SDK agent: the coordinator brain.

This is the most critical agent in the system. It synthesizes ALL worker
outputs and produces SPECIFIC action briefs (Principle #1: never delegate
understanding). It is the brain; workers are the hands.

Principles encoded:
#1 Never delegate understanding — orchestrator synthesizes, never passes through
#3 Coordinator mode — never executes tools directly, only reads and dispatches
#8 Worker results are internal signals — orchestrator talks to user via issues
#11 Research → Synthesis → Implementation → Verification
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, read_scratchpad, run_agent  # noqa: E402

# The orchestrator's core system prompt (Principle #1)
ORCHESTRATOR_SYSTEM_SUFFIX = """
## Your Role: Coordinator (NOT an Executor)

You are the BRAIN of the forensic-accounting-toolkit agent team.
You NEVER execute tasks directly. You read worker results, SYNTHESIZE them,
and produce SPECIFIC action briefs with enough detail that a worker agent
(or human) can execute without needing to understand the context.

## Critical Anti-Pattern (NEVER do this)

WRONG: "The convention audit found issues. Please fix them."
WRONG: "Based on the test results, investigate the failures."
WRONG: "Run the triage scan and handle whatever you find."

These delegate UNDERSTANDING, not just execution. You must do the understanding.

## Correct Pattern (ALWAYS do this)

RIGHT: "kr-beneish/pyproject.toml line 3: [build-system] requires list is
       ['setuptools'] but must be ['hatchling']. Replace line 3 with:
       requires = ['hatchling']
       This was introduced in the 2026-03-15 refactor commit."

RIGHT: "kr-derivatives test failure: test_moneyness_calculation fails because
       price_volume.parquet is 23 days old (threshold: 20 days). Run
       bash ecosystem.sh copy-parquets to refresh, then re-run tests."

## Your Workflow Each Run

1. RESEARCH: Read ALL available worker scratchpad artifacts
2. SYNTHESIS: Cross-reference findings — find patterns, cascade risks, root causes
3. ACTION BRIEFS: Produce SPECIFIC, file-level briefs with line numbers when possible
4. DISPATCH: Create GitHub issues with the briefs (one issue per distinct problem)
5. VERIFY: Check if issues from PREVIOUS orchestrator run were resolved

## Escalation

Write to _scratchpad/escalation.md if you find:
- Test suite regression introduced by recent commits
- Three or more consecutive unresolved P0 issues
- Any needed destructive git operation
- Any unrecognized repo structure
"""

TASK_PROMPT = """
## Orchestrator Run — Synthesize All Worker Outputs

### Step 1: Read All Available Scratchpad Files

Read these files (use the Read tool, not Bash):
- _scratchpad/test-results.json (from tier1-tests — daily)
- _scratchpad/triage.json (from tier2-triage — daily)
- _scratchpad/convention-audit.json (from tier3-convention-audit — weekly)
- _scratchpad/doc-drift.json (from tier1-doc-drift — daily)
- _scratchpad/count-sync.json (from tier1-count-sync — daily)
- _scratchpad/data-validation.json (from tier2-data-validate — on-demand)
- _scratchpad/pipeline.json (from tier3-pipeline — weekly)

If any file is missing, note it but continue — not all agents run daily.

### Step 2: Synthesize Ecosystem Health

Cross-reference ALL inputs to produce a coherent picture:
- If test failures exist AND convention audit shows recent drift in same repo
  → these may be related (drift caused the failure)
- If data is stale AND kr-derivatives tests fail
  → data staleness is root cause (fix data first, then re-test)
- If board has P0 AI items that are also in triage's blocked_items
  → these need human action (flag as needs-human, not AI-actionable)
- If doc drift exists in repos that had recent commits
  → developer introduced it (higher urgency than inherited drift)

### Step 3: Produce SPECIFIC Action Briefs

For EACH actionable issue, write a brief containing:
- repo: which repo
- file: exact file path (relative to repo root)
- line: line number if applicable
- change: exact change description (what to add/remove/modify)
- why: root cause explanation, not symptom
- command: the exact command to fix it (if applicable)
- priority: P0-P3
- ai_actionable: true if an agent can fix it autonomously

### Step 4: Write orchestrator.json

Write to _scratchpad/orchestrator.json:
{
  "generated_at": "<ISO>",
  "ecosystem_health_score": "<N>/10",
  "health_narrative": "<2-3 sentences synthesizing the state>",
  "action_briefs": [
    {
      "id": "ORCH-<date>-<N>",
      "priority": "P0|P1|P2|P3",
      "repo": "<repo>",
      "file": "<path or null>",
      "line": <int or null>,
      "category": "TEST_FAILURE|CONVENTION_DRIFT|DOC_DRIFT|DATA_STALE|COUNT_DRIFT|BOARD_STALE",
      "change": "<exact change>",
      "why": "<root cause>",
      "command": "<command or null>",
      "ai_actionable": true|false,
      "source_workers": ["test-results", "triage"]
    }
  ],
  "needs_human": [
    {"item": "<description>", "reason": "<why>"}
  ],
  "verification": {
    "previous_issues_checked": <int>,
    "resolved_since_last_run": <int>,
    "persistent_unresolved": <int>
  },
  "escalation_needed": false
}

### Step 5: Verify Previous Issues

Use the Bash tool to check:
```bash
gh issue list --label agent-task --state open --json number,title,createdAt | head -50
```

For issues older than 7 days with priority:p0 label — they are persistent failures.
Record in verification.persistent_unresolved.

If 3+ P0 issues are >7 days old, set escalation_needed: true.
"""


async def main() -> None:
    static_context = load_context()
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")

    # Pre-load available scratchpad files to include in prompt
    available_files = []
    scratchpad = Path(workspace) / "_scratchpad"
    for fname in ["test-results.json", "triage.json", "convention-audit.json",
                  "doc-drift.json", "count-sync.json", "data-validation.json", "pipeline.json"]:
        fpath = scratchpad / fname
        if fpath.exists():
            available_files.append(f"- {fname} (available)")
        else:
            available_files.append(f"- {fname} (NOT AVAILABLE — agent may not have run yet)")

    availability_note = (
        "\n### Available Scratchpad Files\n" + "\n".join(available_files) + "\n"
    )

    prompt = availability_note + TASK_PROMPT

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=static_context + ORCHESTRATOR_SYSTEM_SUFFIX,
        allowed_tools=["Read", "Bash", "Glob"],
        permission_mode="bypassPermissions",
        max_turns=20,
        max_budget_usd=1.00,
        model="claude-sonnet-4-6",
        cwd=workspace,
    )

    print("Running orchestrator agent (Sonnet)...", file=sys.stderr)
    messages = await run_agent(
        prompt,
        options,
        escalation_context="Orchestrator synthesis failed. Review all _scratchpad/*.json files manually.",
    )

    from _sdk_helpers import collect_text
    text = collect_text(messages)

    # Prefer orchestrator.json if agent wrote it directly via Write tool
    agent_written = scratchpad / "orchestrator.json"
    if agent_written.exists():
        try:
            result = json.loads(agent_written.read_text(encoding="utf-8"))
            print("[orchestrator] using agent-written orchestrator.json", file=sys.stderr)
        except json.JSONDecodeError:
            result = None
    else:
        result = None

    # Fall back: extract JSON block from agent text output
    if result is None:
        import re
        for pat in [r"```json\s*(\{.*?\})\s*```", r"```\s*(\{.*?\})\s*```"]:
            m = re.search(pat, text, re.DOTALL)
            if m:
                try:
                    result = json.loads(m.group(1))
                    break
                except json.JSONDecodeError:
                    pass
        if result is None:
            try:
                result = json.loads(text.strip())
            except json.JSONDecodeError:
                result = {"raw_output": text[:2000], "error": "output not structured JSON", "action_briefs": []}

    write_scratchpad("orchestrator.json", result)

    # Check for escalation
    if result.get("escalation_needed"):
        esc_path = scratchpad / "escalation.md"
        esc_path.write_text(
            f"# Escalation — {result.get('generated_at', 'unknown')}\n\n"
            f"## Reason\n{result.get('health_narrative', 'Multiple unresolved P0 issues.')}\n\n"
            f"## Unresolved P0 Issues\n{result.get('verification', {}).get('persistent_unresolved', '?')} issues > 7 days old\n",
            encoding="utf-8",
        )
        print("[ESCALATION] escalation.md written — human review required", file=sys.stderr)

    briefs = result.get("action_briefs", [])
    print(f"\n[orchestrator] Health: {result.get('ecosystem_health_score', '?')}/10 | "
          f"{len(briefs)} action briefs", file=sys.stderr)

    # Create GitHub issues for actionable briefs
    _create_issues(briefs, workspace)


def _create_issues(briefs: list, workspace: str) -> None:
    """Create GitHub issues for each actionable brief (Principle #8)."""
    p0_p1 = [b for b in briefs if b.get("priority") in ("P0", "P1")]
    other = [b for b in briefs if b.get("priority") in ("P2", "P3")]

    # Create individual issues for P0/P1
    for brief in p0_p1:
        _create_issue(brief)

    # Batch P2/P3 into one issue to reduce noise
    if other:
        _create_batched_issue(other)


def _create_issue(brief: dict) -> None:
    repo = brief.get("repo", "unknown")
    priority = brief.get("priority", "P3")
    category = brief.get("category", "GENERAL")
    change = brief.get("change", "See brief.")
    why = brief.get("why", "")
    command = brief.get("command")
    file_ref = brief.get("file", "")
    line_ref = brief.get("line")

    location = f"`{file_ref}`" + (f" line {line_ref}" if line_ref else "")

    body = f"""## {category} — `{repo}`

    **Priority:** {priority}
    **AI-actionable:** {brief.get('ai_actionable', True)}
    **Source workers:** {', '.join(brief.get('source_workers', []))}

    ### Location
    {location or 'See description'}

    ### Required Change
    {change}

    ### Root Cause
    {why}

    {f'### Command{chr(10)}```bash{chr(10)}{command}{chr(10)}```' if command else ''}

    ---
    *Generated by orchestrator agent — Brief ID: {brief.get('id', 'unknown')}*
    """

    labels = ["agent-task", f"priority:{priority.lower()}"]
    if not brief.get("ai_actionable", True):
        labels.append("needs-human")

    result = subprocess.run([
        "gh", "issue", "create",
        "--title", f"[{priority}] [{category}] {repo}: {change[:60]}",
        "--body", body,
        "--label", ",".join(labels),
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"[issue] Created: {result.stdout.strip()}", file=sys.stderr)
    else:
        print(f"[issue] Skipped ({result.stderr.strip()[:100]})", file=sys.stderr)


def _create_batched_issue(briefs: list) -> None:
    if not briefs:
        return

    items = "\n".join(
        f"- [{b.get('priority','?')}] `{b.get('repo','?')}`: {b.get('change','')[:100]}"
        for b in briefs
    )

    body = f"""## Batched P2/P3 Action Items

    {len(briefs)} lower-priority issues from latest orchestrator run.

    ### Items
    {items}

    See `_scratchpad/orchestrator.json` for full briefs.
    ---
    *Generated by orchestrator agent*
    """

    subprocess.run([
        "gh", "issue", "create",
        "--title", f"[P2/P3] Batched: {len(briefs)} lower-priority items",
        "--body", body,
        "--label", "agent-task,priority:p2",
    ], capture_output=True, text=True)


if __name__ == "__main__":
    asyncio.run(main())
