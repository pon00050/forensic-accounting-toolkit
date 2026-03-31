#!/usr/bin/env python3
"""PreToolUse hook: block destructive git and shell operations.

Intercepts Bash tool calls before execution and denies commands that are
hard or impossible to reverse:
  - git push --force / -f
  - git reset --hard
  - git branch -D (delete branch)
  - rm -rf targeting project directories

Always exits 0. Outputs a JSON denial response when a match is found.
"""
import json
import re
import sys

DANGEROUS_PATTERNS = [
    (r"git\s+push\s+.*(--force|-f)(\s|$)", "Force push can destroy published commit history. Push a new commit instead."),
    (r"git\s+reset\s+--hard", "git reset --hard discards uncommitted work permanently. Stash or commit first."),
    (r"git\s+branch\s+-D\b", "Deleting a branch is irreversible if it's the only reference to those commits."),
    (r"rm\s+(-rf|-fr|--recursive)\s+.*Projects/", "Recursive delete inside Projects/ is not allowed through Claude."),
]

try:
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

for pattern, reason in DANGEROUS_PATTERNS:
    if re.search(pattern, command):
        response = {
            "hookSpecificOutput": {
                "permissionDecision": {
                    "behavior": "deny",
                    "message": f"[guard] Blocked: {reason}\n\nIf you genuinely need to run this, do it directly in the terminal outside Claude Code."
                }
            }
        }
        print(json.dumps(response))
        sys.exit(0)

sys.exit(0)
