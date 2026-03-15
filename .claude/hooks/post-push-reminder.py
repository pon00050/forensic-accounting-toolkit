#!/usr/bin/env python3
"""PostToolUse hook: remind to update board and CHANGELOG after git push.

Fires after any Bash command containing 'git push'. Outputs a checklist
to stdout so Claude sees it and can act on it.
"""
import json
import sys

try:
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

if "git push" not in command:
    sys.exit(0)

# Don't fire for the toolkit hub itself (those pushes ARE the bookkeeping)
if "forensic-accounting-toolkit" in command:
    sys.exit(0)

print(
    "[post-push] Changes pushed. Bookkeeping checklist:\n"
    "  1. Update the board item status (gh project item-edit)\n"
    "  2. Log what was done in forensic-accounting-toolkit/CHANGELOG.md\n"
    "  3. Update ECOSYSTEM.md if publication/blocker status changed\n"
    "  4. Commit and push the toolkit hub\n"
    "  Or use /done to handle all of this automatically."
)
sys.exit(0)
