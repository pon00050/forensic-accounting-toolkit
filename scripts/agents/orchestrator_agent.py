"""
orchestrator_agent.py — Sonnet SDK agent: the coordinator brain.

This is the most critical agent in the system. It synthesizes ALL worker
outputs and produces SPECIFIC action briefs (Principle #1: never delegate
understanding). It is the brain; workers are the hands.

Principles encoded:
#1 Never delegate understanding — orchestrator synthesizes, never passes through
#3 Coordinator mode — ZERO tools; all data pre-injected by Python wrapper
#7 Prompt cache — static CONTEXT.md prefix shared across all agents
#8 Worker results are internal signals — orchestrator talks to user via issues
#11 Research → Synthesis → Implementation → Verification
#15 Policy bundle — explicit tool/model/permission/isolation policy per agent
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, run_agent  # noqa: E402

# ── Policy bundle (MM#15) ─────────────────────────────────────────────────────

POLICY = {
    "tool_policy": "NONE — coordinator receives pre-injected data; no tool calls permitted",
    "model_policy": "claude-sonnet-4-6 — synthesis requires Sonnet reasoning depth",
    "permission_policy": "bypassPermissions — read-only synthesis; no filesystem writes via agent",
    "isolation_policy": "coordinator-mode — CLAUDE_CODE_COORDINATOR_MODE=true must be set",
    "budget_usd": 1.00,
    "max_turns": 5,  # coordinator should synthesize in 1-2 turns; 5 is a hard cap
}

# ── System prompt ─────────────────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM_SUFFIX = f"""
## Your Role: Coordinator (NOT an Executor)

You are the BRAIN of the forensic-accounting-toolkit agent team.
You operate in COORDINATOR MODE — you have NO tools available.
ALL data you need has been pre-injected into this prompt.
Your only output is synthesized analysis and a structured JSON object.

Policy: {json.dumps(POLICY, indent=2)}

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

1. RESEARCH: Analyze ALL pre-injected worker scratchpad data below
2. SYNTHESIS: Cross-reference findings — find patterns, cascade risks, root causes
3. ACTION BRIEFS: Produce SPECIFIC, file-level briefs with line numbers when possible
4. VERIFICATION: Check the pre-injected open-issues data for unresolved P0s

## Escalation

Include escalation_needed: true in your JSON output if you find:
- Test suite regression introduced by recent commits
- Three or more consecutive unresolved P0 issues
- Any needed destructive git operation
- Any unrecognized repo structure
"""

# ── Task prompt template ──────────────────────────────────────────────────────

TASK_PROMPT_HEADER = """
## Orchestrator Run — Synthesize All Pre-Injected Worker Data

All scratchpad artifacts and the current open-issue list have been injected below.
You have NO tools — synthesize entirely from the provided data.

### Step 1: Review Pre-Injected Data

Read all sections marked ## PRE-INJECTED below. Note which workers ran
(have data) and which did not (marked NOT AVAILABLE).

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

### Step 4: Output orchestrator.json

Your response MUST end with a JSON code block in exactly this format:

```json
{
  "generated_at": "<ISO>",
  "ecosystem_health_score": "<N>",
  "health_narrative": "<2-3 sentences synthesizing the state>",
  "action_briefs": [
    {
      "id": "ORCH-<date>-<N>",
      "priority": "P0|P1|P2|P3",
      "repo": "<repo>",
      "file": "<path or null>",
      "line": null,
      "category": "TEST_FAILURE|CONVENTION_DRIFT|DOC_DRIFT|DATA_STALE|COUNT_DRIFT|BOARD_STALE",
      "change": "<exact change>",
      "why": "<root cause>",
      "command": "<command or null>",
      "ai_actionable": true,
      "source_workers": ["test-results", "triage"]
    }
  ],
  "needs_human": [
    {"item": "<description>", "reason": "<why>"}
  ],
  "verification": {
    "previous_issues_checked": 0,
    "resolved_since_last_run": 0,
    "persistent_unresolved": 0
  },
  "escalation_needed": false
}
```

No prose after the JSON block.
"""

# Cap per scratchpad file to stay within token budget
_FILE_CHAR_LIMIT = 8000


def _load_suppress_list() -> str:
    """Load orchestrator_suppress.json and format as a system prompt section."""
    suppress_path = Path(__file__).parent / "orchestrator_suppress.json"
    if not suppress_path.exists():
        return ""
    try:
        data = json.loads(suppress_path.read_text(encoding="utf-8"))
        items = data.get("suppress", [])
        if not items:
            return ""
        lines = ["## DO NOT RECOMMEND — Suppressed Items\n",
                 "The following are deliberately deferred by the project owner.",
                 "Do NOT include them in action_briefs. Do NOT create issues for them.\n"]
        for item in items:
            lines.append(f"- repo={item['repo']!r}, keyword={item['keyword']!r}: {item['reason']}")
        return "\n".join(lines) + "\n"
    except Exception:
        return ""


async def main() -> None:
    static_context = load_context()
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    scratchpad = Path(workspace) / "_scratchpad"

    # ── Pre-inject all scratchpad files (MM#3 coordinator purity) ────────────
    injected_sections: list[str] = []

    worker_files = [
        "test-results.json",
        "triage.json",
        "convention-audit.json",
        "doc-drift.json",
        "count-sync.json",
        "data-validation.json",
        "pipeline.json",
        "open-issues.json",  # pre-fetched by orchestrator.yml step
    ]

    for fname in worker_files:
        fpath = scratchpad / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8", errors="replace")
            if len(content) > _FILE_CHAR_LIMIT:
                content = content[:_FILE_CHAR_LIMIT] + "\n... [TRUNCATED]"
            injected_sections.append(
                f"## PRE-INJECTED: {fname}\n```json\n{content}\n```"
            )
        else:
            injected_sections.append(
                f"## PRE-INJECTED: {fname}\n(NOT AVAILABLE — worker may not have run yet)"
            )

    pre_injected_block = "\n\n".join(injected_sections)
    prompt = TASK_PROMPT_HEADER + "\n\n---\n\n" + pre_injected_block

    suppress_section = _load_suppress_list()

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=static_context + ORCHESTRATOR_SYSTEM_SUFFIX + suppress_section,
        allowed_tools=[],   # MM#3: coordinator ZERO tools — synthesize pre-injected data only
        permission_mode="bypassPermissions",
        max_turns=POLICY["max_turns"],
        max_budget_usd=POLICY["budget_usd"],
        model=POLICY["model_policy"].split()[0],  # "claude-sonnet-4-6"
        cwd=workspace,
    )

    print("Running orchestrator agent (Sonnet) — coordinator mode, no tools...", file=sys.stderr)
    messages = await run_agent(
        prompt,
        options,
        escalation_context="Orchestrator synthesis failed. Review all _scratchpad/*.json files manually.",
        agent_name="orchestrator_agent",
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
    # NOTE: _create_issues() mutates briefs in-place with issue_number fields,
    # then we re-write orchestrator.json so the dispatch step can read them.
    if result.get("escalation_needed"):
        esc_path = scratchpad / "escalation.md"
        esc_path.write_text(
            f"# Escalation — {result.get('generated_at', 'unknown')}\n\n"
            f"## Reason\n{result.get('health_narrative', 'Multiple unresolved P0 issues.')}\n\n"
            f"## Unresolved P0 Issues\n{result.get('verification', {}).get('persistent_unresolved', '?')} issues > 7 days old\n",
            encoding="utf-8",
        )
        print("[ESCALATION] escalation.md written — human review required", file=sys.stderr)

    # Python-side suppress filter (safety net — agent may still include suppressed items)
    suppress_path = Path(__file__).parent / "orchestrator_suppress.json"
    if suppress_path.exists():
        try:
            suppress_data = json.loads(suppress_path.read_text(encoding="utf-8"))
            suppress_rules = suppress_data.get("suppress", [])
            original_count = len(result.get("action_briefs", []))
            result["action_briefs"] = [
                b for b in result.get("action_briefs", [])
                if not any(
                    b.get("repo") == rule["repo"] and rule["keyword"].lower() in
                    (b.get("change", "") + b.get("why", "") + b.get("category", "")).lower()
                    for rule in suppress_rules
                )
            ]
            filtered = original_count - len(result["action_briefs"])
            if filtered:
                print(f"[suppress] Filtered {filtered} suppressed item(s)", file=sys.stderr)
        except Exception:
            pass

    briefs = result.get("action_briefs", [])
    print(f"\n[orchestrator] Health: {result.get('ecosystem_health_score', '?')} | "
          f"{len(briefs)} action briefs", file=sys.stderr)

    # Load pre-fetched open issues for dedup
    open_issues: list = []
    open_issues_path = scratchpad / "open-issues.json"
    if open_issues_path.exists():
        try:
            open_issues = json.loads(open_issues_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Create GitHub issues for actionable briefs.
    # _create_issues() mutates each brief in-place with issue_number so the
    # dispatch step in orchestrator.yml can include it in the Tier 4 payload
    # and Tier 4 can close the originating issue after auto-merge.
    _create_issues(briefs, workspace, open_issues)

    # Re-write orchestrator.json now that briefs have issue_number populated.
    write_scratchpad("orchestrator.json", result)


def _create_issues(briefs: list, workspace: str, open_issues: list) -> None:
    """Create GitHub issues for each actionable brief (Principle #8)."""
    p0_p1 = [b for b in briefs if b.get("priority") in ("P0", "P1")]
    other = [b for b in briefs if b.get("priority") in ("P2", "P3")]

    for brief in p0_p1:
        _create_issue(brief, open_issues)

    if other:
        _create_batched_issue(other, open_issues)


def _create_issue(brief: dict, open_issues: list) -> None:
    repo = brief.get("repo", "unknown")
    priority = brief.get("priority", "P3")
    category = brief.get("category", "GENERAL")

    # Dedup: skip if an open issue already exists for this repo + category
    for oi in open_issues:
        oi_title = oi.get("title", "")
        oi_labels = [
            (l.get("name", "") if isinstance(l, dict) else str(l))
            for l in oi.get("labels", [])
        ]
        if (repo in oi_title and category in oi_title and "agent-task" in oi_labels):
            existing_num = oi.get("number")
            print(f"[issue] Skipping {repo}/{category} — already open as #{existing_num}", file=sys.stderr)
            brief["issue_number"] = existing_num
            return
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
        issue_url = result.stdout.strip()
        print(f"[issue] Created: {issue_url}", file=sys.stderr)
        # Parse issue number from URL (e.g. .../issues/42) and write back to
        # the brief in-place so the dispatch step can include it in the Tier 4
        # payload, enabling Tier 4 to close the issue after auto-merge.
        try:
            issue_num = int(issue_url.rstrip("/").split("/")[-1])
            brief["issue_number"] = issue_num
        except (ValueError, IndexError, AttributeError):
            pass  # non-fatal — dispatch will fall back to open-issues.json lookup
    else:
        print(f"[issue] Skipped ({result.stderr.strip()[:100]})", file=sys.stderr)


def _create_batched_issue(briefs: list, open_issues: list) -> None:
    if not briefs:
        return

    # Dedup: skip if an open P2/P3 batched issue already exists from this run cycle
    for oi in open_issues:
        oi_title = oi.get("title", "")
        oi_labels = [
            (l.get("name", "") if isinstance(l, dict) else str(l))
            for l in oi.get("labels", [])
        ]
        if ("Batched" in oi_title or "P2/P3" in oi_title) and "agent-task" in oi_labels:
            print(f"[issue] Skipping batched P2/P3 — already open as #{oi.get('number')}", file=sys.stderr)
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
