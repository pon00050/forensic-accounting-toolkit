#!/usr/bin/env python3
"""PostToolUse hook: detect test count drift after a git commit.

Fires after any Bash command containing 'git commit'. Runs pytest --co -q
in the committed repo and compares the count to hub CLAUDE.md. If they
differ, warns Claude to update the hub documentation.

Designed to be fast and silent when counts match. Skips repos with no
test suites, and skips if pytest fails to run.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HUB = Path("C:/Users/pon00/Projects/forensic-accounting-toolkit")
HUB_CLAUDE = HUB / "CLAUDE.md"

try:
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

# Only fire on actual commits, not git status/log/diff/push/etc.
if "git commit" not in command:
    sys.exit(0)

# Detect repo path from -C flag (e.g. git -C /path/to/repo commit ...)
m = re.search(r"git -C ([^\s]+)", command)
if not m:
    # No -C flag — hook cwd is the hub, not the committed repo; skip
    sys.exit(0)

try:
    repo_path = Path(m.group(1).strip("'\"")).resolve()
except Exception:
    sys.exit(0)

repo_name = repo_path.name

# Skip if no tests directory
if not (repo_path / "tests").exists():
    sys.exit(0)

# Run pytest collection count (--co is fast: no test execution)
try:
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/", "--co", "-q", "--no-header"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    m = re.search(r"(\d+) tests? collected", result.stdout + result.stderr)
    if not m:
        sys.exit(0)
    actual = int(m.group(1))
except Exception:
    sys.exit(0)

# Read hub CLAUDE.md to find claimed count for this repo
try:
    claude_text = HUB_CLAUDE.read_text(encoding="utf-8")
    pattern = rf"\|\s*\*\*{re.escape(repo_name)}\*\*\s*\|[^|]+\|[^|]+\|\s*(\d+)\s*\|"
    m = re.search(pattern, claude_text)
    if not m:
        sys.exit(0)
    claimed = int(m.group(1))
except Exception:
    sys.exit(0)

if actual == claimed:
    sys.exit(0)

print(
    f"[TEST COUNT DRIFT] {repo_name}: hub CLAUDE.md says {claimed}, actual is {actual}\n"
    f"  Update both CLAUDE.md and ECOSYSTEM.md to {actual}.\n"
    f"  Or run /done to handle this automatically."
)

sys.exit(0)
