"""
data_validate_agent.py — Haiku SDK agent: parquet validation report.

PURPOSE: Verify that pipeline parquet outputs are correct, not just present.
Follows Principle #5: verification = proving it works, not confirming it exists.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, run_agent  # noqa: E402

TASK_PROMPT = """
## Your Task: Parquet Data Validation

You must PROVE the pipeline outputs are correct, not just confirm they exist.
"File exists" is not a passing check. You must verify semantic correctness.

## Files to Validate

The pipeline produces parquet files in the krff-shell repo:
- `$WORKSPACE/../krff-shell/01_Data/processed/price_volume.parquet`
- `$WORKSPACE/../krff-shell/01_Data/processed/cb_bw_events.parquet`
- `$WORKSPACE/../krff-shell/01_Data/processed/corp_actions.parquet`

## Validation Checks (Principle #5 — prove correctness)

For EACH file, run Python checks using the Bash tool:

```python
import pandas as pd, sys
df = pd.read_parquet('<path>')

# Check 1: Not empty
assert len(df) > 0, f"EMPTY: {len(df)} rows"

# Check 2: Not all nulls
null_rate = df.isnull().mean().max()
assert null_rate < 0.5, f"HIGH_NULLS: max null rate {null_rate:.1%}"

# Check 3: Semantically meaningful row count (not suspiciously small)
assert len(df) > 100, f"TOO_FEW_ROWS: {len(df)}"

# price_volume specific:
if 'corp_code' in df.columns:
    assert df['corp_code'].nunique() > 100, f"TOO_FEW_COMPANIES: {df['corp_code'].nunique()}"
if 'close' in df.columns:
    assert (df['close'] > 0).mean() > 0.9, "PRICES_MOSTLY_ZERO"

# cb_bw specific:
if 'issue_type' in df.columns:
    assert df['issue_type'].isin(['CB','BW','EB']).any(), "NO_VALID_ISSUE_TYPES"

print(f"OK: {len(df)} rows, {len(df.columns)} columns, max_null={null_rate:.1%}")
```

## Output Schema

Your FINAL response MUST end with a JSON code block. No prose after it.

Write to _scratchpad/data-validation.json:
{
  "generated_at": "<ISO timestamp>",
  "files": {
    "price_volume.parquet": {
      "exists": true|false,
      "size_bytes": <int>,
      "row_count": <int>,
      "column_count": <int>,
      "max_null_rate": <float>,
      "status": "PASS|FAIL|MISSING",
      "checks": [{"name": "<check>", "result": "PASS|FAIL", "detail": "<detail>"}]
    },
    "cb_bw_events.parquet": {...},
    "corp_actions.parquet": {...}
  },
  "overall_status": "PASS|FAIL|PARTIAL",
  "summary": "<one sentence>"
}

## Rules
- Use the Bash tool to run Python validation inline.
- If a file doesn't exist, mark it MISSING and continue — don't abort.
- Be skeptical. An empty dataframe that "passes" file existence is a failure.
"""


async def main() -> None:
    static_context = load_context()
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")

    prompt = TASK_PROMPT.replace("$WORKSPACE", workspace)

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=(
            static_context
            + "\n\nYou are the data validation agent. Your job is to PROVE correctness, not confirm existence."
        ),
        allowed_tools=["Bash", "Read"],
        permission_mode="bypassPermissions",
        max_turns=15,
        max_budget_usd=0.30,
        model="claude-haiku-4-5-20251001",
        cwd=workspace,
    )

    print("Running data validation agent (Haiku)...", file=sys.stderr)
    messages = await run_agent(
        prompt,
        options,
        escalation_context="Data validation failed. Check parquet files in krff-shell/01_Data/processed/",
    )

    from _sdk_helpers import collect_text
    text = collect_text(messages)

    # Try to extract JSON
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
        result = {
            "raw_output": text,
            "overall_status": "UNKNOWN",
            "files": {},
            "summary": "Agent output was not structured JSON — review manually",
        }

    write_scratchpad("data-validation.json", result)
    print(f"\n[data-validate] Overall: {result.get('overall_status', 'UNKNOWN')}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
