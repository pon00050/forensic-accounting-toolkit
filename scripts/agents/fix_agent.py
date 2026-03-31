"""
fix_agent.py — Sonnet SDK agent: fix a broken test suite.

PURPOSE: Given a fix brief (category, repo, description), investigate the
failure, apply a targeted code fix, self-verify with tests, and write
fix-result.json for the independent verify_agent to review.

Dispatched by tier4-autofix.yml via repository_dispatch with event_type=agent-fix.

Note: This agent writes status="self_verified" — NOT "fixed". The authoritative
"fixed" verdict comes only from verify_agent.py (MM#5 self-verification gate).

Policy: MM#15 policy bundle — explicit per-agent policy.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, run_agent, collect_text, bootstrap_target_hooks  # noqa: E402

# ── Policy bundle (MM#15) ─────────────────────────────────────────────────────

POLICY = {
    "tool_policy": "Read + Grep + Glob + Edit + Write + Bash — full tool set for diagnosis and repair",
    "model_policy": "claude-sonnet-4-6 — code fixes require Sonnet reasoning depth",
    "permission_policy": "bypassPermissions — may edit source files in _target_repo only",
    "isolation_policy": "worker-session — independent from verify_agent (MM#5)",
    "budget_usd": 2.00,
    "max_turns": 25,
}

TASK_PROMPT_TEMPLATE = """
## Your Task: Fix a Code Issue

You have been dispatched to investigate and fix a problem in the Korean forensic accounting ecosystem.

### Fix Brief
```json
{brief_json}
```

### Environment

- Target repo is checked out at: `{repo_path}`
- Scratchpad dir (write fix-result.json here): `{scratchpad_path}`
- Repo CLAUDE.md: `{repo_path}/CLAUDE.md` (read this first for conventions)

### Procedure

**Step 1 — Read CLAUDE.md** to understand the repo's architecture and conventions.

**Step 2 — Reproduce the problem.** For TEST_FAIL:
```
cd {repo_path} && uv run pytest tests/ -q 2>&1 | head -80
```
For other categories, read the files mentioned in the brief.

**Step 3 — Diagnose.** Read the failing test(s) and the source code they test.
Identify the exact root cause before touching anything.

**Step 4 — Fix.** Edit the source file (NEVER the test file). Make the smallest
targeted change that addresses the root cause. Don't clean up surrounding code
or add unrelated improvements.

**Step 5 — Verify.** Run the full test suite:
```
cd {repo_path} && uv run pytest tests/ -q
```
All tests must pass. If a test was already failing before your change, note it
but don't include it in your pass count.

**Step 6 — Write result.** Write to `{scratchpad_path}/fix-result.json`:

If all tests pass after your fix:
```json
{{
  "status": "self_verified",
  "repo": "{repo}",
  "changed_files": ["src/pkg/module.py"],
  "summary": "One sentence: what was wrong and what was changed.",
  "test_output": "<last 15 lines of the passing pytest run>"
}}
```

If you cannot fix it (env dependency, human decision needed, not a code bug):
```json
{{
  "status": "needs_human",
  "repo": "{repo}",
  "changed_files": [],
  "summary": "What was tried, why it could not be auto-fixed.",
  "test_output": "<last 15 lines of the failing pytest run>"
}}
```

### Hard Rules

- NEVER modify test files to make tests pass. Fix source code only.
- NEVER mock out or delete failing assertions.
- NEVER modify `data/raw/` — those files are immutable.
- If the failure is caused by missing parquet data files (env issue), write needs_human.
- If fixing requires calling an external API or spending money, write needs_human.
- Max 3 fix attempts — if tests still fail after 3 iterations, write needs_human.
"""


async def main() -> None:
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    scratchpad = workspace / "_scratchpad"

    brief_path = scratchpad / "fix-brief.json"
    if not brief_path.exists():
        print("ERROR: _scratchpad/fix-brief.json not found", file=sys.stderr)
        write_scratchpad("fix-result.json", {
            "status": "error",
            "repo": "unknown",
            "changed_files": [],
            "summary": "fix-brief.json not found in scratchpad",
            "test_output": "",
        })
        sys.exit(1)

    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    repo = brief.get("repo", "")
    category = brief.get("category", "UNKNOWN")

    if not repo:
        print("ERROR: fix-brief.json missing 'repo' field", file=sys.stderr)
        write_scratchpad("fix-result.json", {
            "status": "error",
            "repo": "unknown",
            "changed_files": [],
            "summary": "fix-brief.json missing 'repo' field",
            "test_output": "",
        })
        sys.exit(1)

    # Find the repo checkout — tier4-autofix.yml places it at _target_repo
    repo_path = workspace / "_target_repo"
    if not repo_path.exists():
        # Fallback for local runs: check $PARENT/<repo>
        repo_path = workspace.parent / repo
    if not repo_path.exists():
        print(f"ERROR: repo checkout not found for {repo}", file=sys.stderr)
        write_scratchpad("fix-result.json", {
            "status": "error",
            "repo": repo,
            "changed_files": [],
            "summary": f"Repo not found at _target_repo or ../{repo}",
            "test_output": "",
        })
        sys.exit(1)

    # Bootstrap no-op hook stubs in _target_repo/.claude/hooks/ before launching
    # the SDK session. Once the agent cd's into _target_repo, Claude Code's
    # persistent shell stays there and all hook lookups become relative to that
    # directory. Missing hooks block every Bash call (PreToolUse gate).
    bootstrap_target_hooks(repo_path)

    static_context = load_context()

    prompt = TASK_PROMPT_TEMPLATE.format(
        brief_json=json.dumps(brief, indent=2),
        repo=repo,
        repo_path=str(repo_path),
        scratchpad_path=str(scratchpad),
        category=category,
    )

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=(
            static_context
            + f"\n\nPolicy: {json.dumps(POLICY, indent=2)}\n\n"
            + "You are an autonomous code-fix agent. Your only job is to fix "
            "the specific issue described in the brief and self-verify with tests. "
            "Write status='self_verified' when tests pass — an independent verify_agent "
            "will provide the authoritative verdict (MM#5)."
        ),
        allowed_tools=["Read", "Grep", "Glob", "Edit", "Write", "Bash"],
        permission_mode="bypassPermissions",
        max_turns=POLICY["max_turns"],
        max_budget_usd=POLICY["budget_usd"],
        model=POLICY["model_policy"].split()[0],
        cwd=str(workspace),
    )

    print(f"Running fix agent (Sonnet) for {repo} [{category}]...", file=sys.stderr)
    messages = await run_agent(
        prompt,
        options,
        escalation_context=(
            f"Fix agent failed for {repo} [{category}]. "
            f"Manual investigation needed. Brief: {json.dumps(brief)}"
        ),
        agent_name="fix_agent",
    )

    text = collect_text(messages)

    # Verify fix-result.json was written by the agent
    result_path = scratchpad / "fix-result.json"
    if not result_path.exists():
        # Try to extract structured result from agent's text output
        extracted = _extract_json(text)
        if extracted and "status" in extracted:
            write_scratchpad("fix-result.json", extracted)
        else:
            write_scratchpad("fix-result.json", {
                "status": "needs_human",
                "repo": repo,
                "changed_files": [],
                "summary": "Agent completed but did not write fix-result.json",
                "test_output": text[-600:] if text else "",
            })

    result = json.loads(result_path.read_text(encoding="utf-8"))
    status = result.get("status", "?")
    summary = result.get("summary", "")[:100]
    print(f"\n[fix-agent] {repo} [{category}] → status={status}", file=sys.stderr)
    print(f"[fix-agent] {summary}", file=sys.stderr)


def _extract_json(text: str) -> dict | None:
    for pat in [r"```json\s*(\{.*?\})\s*```", r"```\s*(\{.*?\})\s*```"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    return None


if __name__ == "__main__":
    asyncio.run(main())
