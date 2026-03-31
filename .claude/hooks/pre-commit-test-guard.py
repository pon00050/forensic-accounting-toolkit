#!/usr/bin/env python3
"""PreToolUse hook: warn before git commit if in a testable repo.

When committing from ANY ecosystem repo that has tests, outputs a reminder
to ensure tests were run. Does NOT block (exit 0) — just reminds.

This is the cross-repo equivalent of krff-shell's per-edit test hook.
It catches commits in repos that lack their own hooks.
"""
import json
import re
import sys
from pathlib import Path

# Repos with tests and their test commands (sourced from ecosystem.conf logic)
# All repos use `uv run pytest tests/ -v` except kr-company-registry (no uv wrapper)
# SYNC: must match ecosystem.conf REPOS_WITH_TESTS (Python cannot source bash)
TESTABLE_REPOS = {
    "kr-company-registry": "pytest tests/ -v",
    "kr-trading-calendar": "uv run pytest tests/ -v",
    "kr-beneish": "uv run pytest tests/ -v",
    "kr-derivatives": "uv run pytest tests/ -v",
    "jfia-forensic": "uv run pytest tests/ -v",
    "kr-enforcement-cases": "uv run pytest tests/ -v",
    "kr-forensic-core": "uv run pytest tests/ -v",
    "krff-shell": "uv run pytest tests/ -v",
    "kr-dart-pipeline": "uv run pytest tests/ -v",
    "kr-anomaly-scoring": "uv run pytest tests/ -v",
    "kr-stat-tests": "uv run pytest tests/ -v",
}

try:
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

# Only check git commit commands
if not re.search(r"git\s+commit", command):
    sys.exit(0)

# Detect which repo we're committing in
for repo_name, test_cmd in TESTABLE_REPOS.items():
    if repo_name in command or f"Projects/{repo_name}" in command:
        print(
            f"[pre-commit] Committing in {repo_name}. "
            f"Verify tests pass: {test_cmd}"
        )
        break
else:
    # Check if we're cd'd into a testable repo (command may not have full path)
    # The cwd is tracked by the shell, so just remind generically
    pass

sys.exit(0)
