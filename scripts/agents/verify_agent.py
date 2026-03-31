"""
verify_agent.py — Sonnet SDK agent: independent post-fix verification.

PURPOSE: Provide an authoritative, independent verdict on whether the fix
applied by fix_agent.py actually resolves the problem.

This agent is launched in a FRESH session — it has no knowledge of what
fix_agent attempted. It proves correctness from first principles (Principle #5).

Self-verification gate: the agent that generates a fix must NEVER be the agent
that approves it (MM#5 self-verification gate prohibition).

Policy: MM#15 policy bundle — explicit per-agent policy.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, run_agent, bootstrap_target_hooks  # noqa: E402

# ── Policy bundle (MM#15) ─────────────────────────────────────────────────────

POLICY = {
    "tool_policy": "Bash + Read only — run tests, read results; no edits permitted",
    "model_policy": "claude-sonnet-4-6 — verification requires same reasoning depth as fix",
    "permission_policy": "bypassPermissions — read-only verification; no file edits",
    "isolation_policy": "fresh-session — must NOT share session with fix_agent",
    "budget_usd": 0.50,
    "max_turns": 8,
}

VERIFY_SYSTEM = f"""
You are the VERIFICATION agent for the forensic-accounting-toolkit ecosystem.

Policy: {json.dumps(POLICY, indent=2)}

Your sole purpose is to PROVE that a code fix is correct by running the actual
test suite and inspecting the results. You did NOT apply the fix — you are an
independent auditor.

## Rules

- NEVER modify any file. You have Read and Bash only.
- Run the full test suite — not just the previously-failing test.
- A fix is PASS only if ALL tests pass (or pre-existing failures are documented).
- If tests pass: write status="pass" to verify-result.json.
- If any test fails: write status="fail" with the failing test names.
- Be skeptical. A test suite with 0 collected tests is a collection failure (fail).
"""

TASK_PROMPT_TEMPLATE = """
## Your Task: Independent Fix Verification

A fix has been applied to `{repo}` (checked out at `{repo_path}`).
You are verifying it independently — you do NOT know what was changed.

### Step 1: Run the full test suite

```bash
cd {repo_path} && uv run pytest tests/ -q 2>&1
```

If uv is not available, try:
```bash
cd {repo_path} && python -m pytest tests/ -q 2>&1
```

### Step 2: Inspect results

- How many tests passed? Failed? Errors?
- Are there any collection errors (0 tests collected)?
- Which specific tests failed, if any?

### Step 3: Write verify-result.json

Write to `{scratchpad_path}/verify-result.json`:

If all tests pass:
```json
{{
  "status": "pass",
  "repo": "{repo}",
  "passed_count": <int>,
  "failed_count": 0,
  "failed_tests": [],
  "test_output": "<last 20 lines of pytest output>"
}}
```

If any test fails or collection error:
```json
{{
  "status": "fail",
  "repo": "{repo}",
  "passed_count": <int>,
  "failed_count": <int>,
  "failed_tests": ["test_name_1", "test_name_2"],
  "test_output": "<last 20 lines of pytest output>"
}}
```

### Hard Rules

- NEVER modify any source file or test file.
- If tests were already failing before the fix (pre-existing), list them under
  `failed_tests` but note "pre-existing" in test_output. Status is still "fail"
  unless the brief explicitly marks them as known-failing.
- A 0-tests-collected result is always "fail" — not "pass".
"""


async def main() -> None:
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    scratchpad = workspace / "_scratchpad"

    # Read the fix brief to know which repo to verify
    brief_path = scratchpad / "fix-brief.json"
    if not brief_path.exists():
        print("ERROR: fix-brief.json not found — cannot verify", file=sys.stderr)
        write_scratchpad("verify-result.json", {
            "status": "fail",
            "repo": "unknown",
            "passed_count": 0,
            "failed_count": 0,
            "failed_tests": [],
            "test_output": "verify-result.json: fix-brief.json not found",
        })
        sys.exit(1)

    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    repo = brief.get("repo", "")

    # Read fix-result.json to confirm fix_agent self-verified
    fix_result_path = scratchpad / "fix-result.json"
    fix_status = "unknown"
    if fix_result_path.exists():
        fix_result = json.loads(fix_result_path.read_text(encoding="utf-8"))
        fix_status = fix_result.get("status", "unknown")

    if fix_status not in ("self_verified", "fixed"):
        # Fix agent did not succeed — no point running tests
        print(f"[verify] fix_agent status={fix_status} — skipping test run", file=sys.stderr)
        write_scratchpad("verify-result.json", {
            "status": "skipped",
            "repo": repo,
            "passed_count": 0,
            "failed_count": 0,
            "failed_tests": [],
            "test_output": f"Skipped: fix_agent status was {fix_status}",
        })
        return

    # Find target repo checkout
    repo_path = workspace / "_target_repo"
    if not repo_path.exists():
        repo_path = workspace.parent / repo
    if not repo_path.exists():
        print(f"ERROR: repo not found for {repo}", file=sys.stderr)
        write_scratchpad("verify-result.json", {
            "status": "fail",
            "repo": repo,
            "passed_count": 0,
            "failed_count": 0,
            "failed_tests": [],
            "test_output": f"Repo not found at _target_repo or ../{repo}",
        })
        sys.exit(1)

    # Bootstrap no-op hook stubs before launching — same reason as fix_agent.
    bootstrap_target_hooks(repo_path)

    static_context = load_context()

    prompt = TASK_PROMPT_TEMPLATE.format(
        repo=repo,
        repo_path=str(repo_path),
        scratchpad_path=str(scratchpad),
    )

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=static_context + "\n\n" + VERIFY_SYSTEM,
        allowed_tools=["Bash", "Read"],   # read-only verification — no edits
        permission_mode="bypassPermissions",
        max_turns=POLICY["max_turns"],
        max_budget_usd=POLICY["budget_usd"],
        model=POLICY["model_policy"].split()[0],
        cwd=str(workspace),
    )

    print(f"Running verify agent (Sonnet) for {repo} [FRESH SESSION]...", file=sys.stderr)
    messages = await run_agent(
        prompt,
        options,
        escalation_context=f"Verification agent failed for {repo}. Manual test run required.",
        agent_name="verify_agent",
    )

    from _sdk_helpers import collect_text
    text = collect_text(messages)

    # Read what the agent wrote
    result_path = scratchpad / "verify-result.json"
    if not result_path.exists():
        # Try to extract from agent text output
        import re
        for pat in [r"```json\s*(\{.*?\})\s*```", r"```\s*(\{.*?\})\s*```"]:
            m = re.search(pat, text, re.DOTALL)
            if m:
                try:
                    result = json.loads(m.group(1))
                    write_scratchpad("verify-result.json", result)
                    break
                except json.JSONDecodeError:
                    pass
        else:
            write_scratchpad("verify-result.json", {
                "status": "fail",
                "repo": repo,
                "passed_count": 0,
                "failed_count": 0,
                "failed_tests": [],
                "test_output": "Verify agent completed but did not write verify-result.json",
            })

    result = json.loads((scratchpad / "verify-result.json").read_text(encoding="utf-8"))
    status = result.get("status")
    print(f"\n[verify-agent] {repo} → status={status} | "
          f"passed={result.get('passed_count',0)} failed={result.get('failed_count',0)}",
          file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
