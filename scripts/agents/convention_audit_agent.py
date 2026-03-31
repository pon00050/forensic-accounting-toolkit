"""
convention_audit_agent.py — Sonnet SDK agent: full 182-check convention audit.

PURPOSE: Prove each repo's compliance with all 14 canonical conventions.
Follows Principle #5: semantic verification, not grep-and-done.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, run_agent, read_scratchpad  # noqa: E402

TASK_PROMPT = """
## Your Task: Full Convention Audit (182 checks)

Audit ALL 13 repos against ALL 14 canonical conventions.
Total checks: 14 × 13 = 182 (some are EXEMPT, still record them).

## The 14 Conventions (from canonical-conventions skill)

1. Build system: hatchling in [build-system] requires
2. Python version: >=3.11 in requires-python (kr-beneish: >=3.10 OK)
3. Package manager: uv only, no requirements.txt
4. Test command: uv run pytest tests/ -v (kr-company-registry: bare pytest OK)
5. uv.lock committed to git (jfia-catalog exempt)
6. conftest.py present in tests/ directory (repos without tests/ exempt)
7. constants.py present in src/ (kr-trading-calendar exempt)
8. Paths module _paths.py or paths.py in src/ (repos with no file I/O exempt)
9. Commit style: feat/fix/docs/refactor/test/chore prefix on last 5 commits
10. .claude/ directory present (jfia-catalog exempt)
11. compile-bytecode = false in [tool.uv] (repos without pyproject.toml exempt)
12. CLAUDE.md present at root
13. ## Known Gaps section in CLAUDE.md (hub/forensic-accounting-toolkit exempt)
14. No stale "kr-forensic-finance" refs in .md/.toml/.conf (reports/ exempt)

## The 13 Repos

All repos are at: {parent_path}/<repo>/

Repos: krff-shell, kr-forensic-core, kr-dart-pipeline, kr-anomaly-scoring,
kr-stat-tests, kr-company-registry, kr-trading-calendar, kr-beneish,
kr-derivatives, jfia-catalog, jfia-forensic, kr-enforcement-cases, kr-real-estate

## Verification Approach (Principle #5)

Use the Bash tool to run actual checks per repo. Examples:

```bash
# Convention 1: parse actual [build-system] table
python3 -c "
import tomllib, pathlib
try:
    data = tomllib.load(open('../krff-shell/pyproject.toml', 'rb'))
    bs = data.get('build-system', {})
    req = bs.get('requires', [])
    print('OK' if any('hatchling' in r for r in req) else f'DRIFT: {req}')
except FileNotFoundError:
    print('MISS: no pyproject.toml')
"

# Convention 9: check commit style semantically
git -C ../kr-beneish log --oneline -5 | grep -cP '^[a-f0-9]+ (feat|fix|docs|refactor|test|chore)' || echo "0 conventional commits"

# Convention 11: check compile-bytecode value (not just presence)
python3 -c "
import tomllib
data = tomllib.load(open('../kr-beneish/pyproject.toml', 'rb'))
uv = data.get('tool', {}).get('uv', {})
cb = uv.get('compile-bytecode')
if cb is False: print('OK')
elif cb is None: print('MISS')
else: print(f'DRIFT: {cb}')
"
```

## Previous Audit Delta

If _scratchpad/convention-audit-prev.json exists, compare to previous run
and report NEW deviations (first appearance) separately from PERSISTENT ones.

## Output Format

Write to _scratchpad/convention-audit.json:
{{
  "generated_at": "<ISO timestamp>",
  "total_checks": 182,
  "ok_count": <int>,
  "drift_count": <int>,
  "miss_count": <int>,
  "exempt_count": <int>,
  "new_deviations_since_last": <int>,
  "repos": {{
    "<repo>": {{
      "score": "<N>/14",
      "conventions": {{
        "1_build_system": "OK|DRIFT|MISS|EXEMPT",
        "2_python_version": "...",
        ...
      }},
      "deviations": [
        {{"convention": "<N_name>", "status": "DRIFT|MISS", "detail": "<actual vs expected>", "is_new": true|false}}
      ]
    }}
  }},
  "top_deviations": [
    {{"severity": "DRIFT|MISS", "repo": "<repo>", "convention": "<name>", "detail": "<detail>", "is_new": true|false}}
  ]
}}

## Rules

- Read-only. Do NOT fix anything.
- Be specific: for DRIFT, show the actual value found AND what's expected.
- Check ALL 14 conventions for ALL 13 repos. Skip none.
- Run efficiently: batch multiple checks per repo in one Bash call.
- Save the full audit to _scratchpad/convention-audit.json when done.
- Copy current audit to _scratchpad/convention-audit-prev.json for next run's delta.
"""


async def main() -> None:
    static_context = load_context()
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    parent = str(Path(workspace).parent)

    # Check for previous audit (for delta reporting)
    prev_audit = read_scratchpad("convention-audit-prev.json")
    prev_note = ""
    if prev_audit:
        prev_date = prev_audit.get("generated_at", "unknown date")
        prev_deviations = prev_audit.get("drift_count", 0) + prev_audit.get("miss_count", 0)
        prev_note = f"\nPrevious audit: {prev_date}, {prev_deviations} deviations.\nReport new vs persistent.\n"

    prompt = TASK_PROMPT.replace("{parent_path}", parent) + prev_note

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=(
            static_context
            + "\n\nYou are the convention auditor. You verify compliance semantically, not just by grep."
        ),
        allowed_tools=["Bash", "Read", "Glob", "Grep"],
        permission_mode="bypassPermissions",
        max_turns=30,
        max_budget_usd=2.00,
        model="claude-sonnet-4-6",
        cwd=workspace,
    )

    print("Running convention audit agent (Sonnet)...", file=sys.stderr)
    messages = await run_agent(
        prompt,
        options,
        escalation_context="Convention audit failed. Check repos at parent directory.",
    )

    from _sdk_helpers import collect_text
    text = collect_text(messages)

    # Extract JSON
    import re
    result = None
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
            result = {"raw_output": text, "total_checks": 182, "error": "output not structured JSON"}

    write_scratchpad("convention-audit.json", result)
    # Save as prev for next run's delta
    write_scratchpad("convention-audit-prev.json", result)

    print(f"\n[convention-audit] {result.get('ok_count','?')} OK, "
          f"{result.get('drift_count','?')} DRIFT, "
          f"{result.get('miss_count','?')} MISS", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
