"""
triage_agent.py — Haiku SDK agent: synthesize triage scan output.

PURPOSE: Transform raw triage-scan.sh output into a ranked action list.
The human reads this every morning to decide what to work on.

Follows Principle #2: full briefing prompt with context, judgment calls,
and specific output schema.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure _sdk_helpers is importable
sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, run_agent  # noqa: E402

TASK_PROMPT = """
## Your Task: Triage Synthesis

You have just received the raw output of triage-scan.sh, a 726-line bash script
that scanned 13 sources across a 13-repo Korean forensic accounting ecosystem:

Sources scanned:
1. GitHub Projects board state (AI-owned Todo items)
2. Git hygiene (uncommitted, unpushed, stale branches)
3. ECOSYSTEM.md backlog
4. Board freshness (claims vs filesystem evidence)
5. Cross-project blockers (cross-issues/)
6. Code signals (TODO/FIXME/HACK/NotImplementedError)
7. Data freshness (parquet file timestamps)
8. CHANGELOG staleness
9. Convention quick-check
10. Doc drift (stale repo name references)
11. Test count drift
12. Strategy alignment
13. Known Gaps table

## Priority Matrix

| Category | Priority |
|----------|----------|
| Test failure | P0 |
| Uncommitted/unpushed changes | P0/P1 |
| Board P0 AI tasks (unblocked) | P1 |
| Data staleness (>20 days) | P1 |
| Board P1 AI tasks | P2 |
| Open stubs in active code | P2 |
| Convention drift | P3 |

## Judgment Rules

- If multiple repos fail tests, prioritize by dependency order:
  kr-forensic-core → kr-dart-pipeline → (kr-anomaly-scoring, kr-stat-tests, krff-shell) → others
  Upstream failures cascade — they block more downstream work.
- Board items with "SEIBRO" or external API dependencies are human-blocked
  even if labeled AI-owned. Flag them as needs-human.
- Data is STALE if any parquet is older than 20 days.
- If no board data available (gh CLI offline), note it but continue with other sources.

## Output Format

Read the triage scan output from the TRIAGE_SCAN_OUTPUT variable in the environment,
or from _scratchpad/triage-scan-raw.txt if present.

Your FINAL response MUST end with a JSON code block in exactly this format.
No prose after the JSON block. The issue display depends entirely on this.

```json
{
  "generated_at": "<ISO timestamp>",
  "mode": "full",
  "summary": {
    "clean_repos": <int>,
    "total_repos": 13,
    "board_todo_ai": <int>,
    "open_stubs": <int>,
    "convention_drift_count": <int>
  },
  "ranked_actions": [
    {
      "priority": "P0|P1|P2|P3",
      "category": "<BOARD|UNCOMMITTED|UNPUSHED|DATA_STALE|TEST_FAIL|STUB|CONVENTION|...>",
      "repo": "<repo name>",
      "description": "<one sentence — what, where, why>",
      "ai_actionable": true|false,
      "suggested_command": "<command or null>"
    }
  ],
  "blocked_items": [
    {"item": "<description>", "reason": "<why human is needed>"}
  ],
  "recommended_next": "<single command>"
}
```

Cap ranked_actions at 8 items. Rank strictly by priority, then impact.
Always provide recommended_next — the single most valuable next command.
"""


async def main() -> None:
    # Load shared static context (Principle #7 — prompt caching)
    static_context = load_context()

    # Read triage scan raw output
    scan_raw_path = Path(os.environ.get("GITHUB_WORKSPACE", ".")) / "_scratchpad" / "triage-scan-raw.txt"
    if scan_raw_path.exists():
        scan_output = scan_raw_path.read_text(encoding="utf-8", errors="replace")
    else:
        scan_output = os.environ.get("TRIAGE_SCAN_OUTPUT", "")

    if not scan_output:
        print("ERROR: No triage scan output found.", file=sys.stderr)
        write_scratchpad("triage.json", {
            "error": "No triage scan output available",
            "ranked_actions": [],
            "recommended_next": "bash triage-scan.sh"
        })
        sys.exit(1)

    # Truncate to ~50K chars to stay within token budget
    if len(scan_output) > 50000:
        scan_output = scan_output[:50000] + "\n[TRUNCATED]"

    prompt = (
        f"{TASK_PROMPT}\n\n"
        f"## Triage Scan Output\n\n```\n{scan_output}\n```"
    )

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=static_context + "\n\nYou are the triage analyst for this ecosystem.",
        allowed_tools=["Read", "Glob", "Write"],
        permission_mode="bypassPermissions",
        max_turns=10,
        max_budget_usd=0.50,
        model="claude-haiku-4-5-20251001",
        cwd=os.environ.get("GITHUB_WORKSPACE", "."),
    )

    print("Running triage agent (Haiku)...", file=sys.stderr)
    messages = await run_agent(
        prompt,
        options,
        escalation_context="Triage synthesis failed. Raw scan output available at _scratchpad/triage-scan-raw.txt",
    )

    # Extract JSON from agent output
    from _sdk_helpers import collect_text
    text = collect_text(messages)

    # Try to parse JSON from the response
    triage_data = _extract_json(text)
    if triage_data is None:
        # Fallback: wrap text output in minimal schema
        triage_data = {
            "raw_output": text,
            "ranked_actions": [],
            "recommended_next": "review triage scan manually",
        }

    write_scratchpad("triage.json", triage_data)
    print("\n[triage] Complete.", file=sys.stderr)

    # Print summary
    actions = triage_data.get("ranked_actions", [])
    print(f"[triage] {len(actions)} ranked actions")
    for a in actions[:5]:
        print(f"  [{a.get('priority','?')}] {a.get('repo','?')}: {a.get('description','')[:80]}")


def _extract_json(text: str) -> dict | None:
    """Extract the first valid JSON object from text."""
    import re
    # Try to find a JSON block
    patterns = [
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
        r"(\{[^{}]*\"ranked_actions\"[^{}]*\})",  # simple match
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    # Try parsing the whole text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    asyncio.run(main())
