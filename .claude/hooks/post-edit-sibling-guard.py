#!/usr/bin/env python3
"""PostToolUse hook: remind to read CLAUDE.md when editing a sibling repo.

Fires after Edit or Write tool calls. If the file being modified lives in
a sibling repo (same Projects/ parent, different directory than the hub),
prints a one-line reminder. This is a soft warning, not a block — it fires
even if you've already read the CLAUDE.md.

The hub itself (forensic-accounting-toolkit) is excluded.
"""
import os, sys as _sys
if os.name != "nt" or os.environ.get("CI"):
    _sys.exit(0)

import json
import sys
from pathlib import Path

HUB_NAME = "forensic-accounting-toolkit"
PROJECTS_MARKERS = [
    "C:/Users/pon00/Projects/",
    "C:\\Users\\pon00\\Projects\\",
    "/c/Users/pon00/Projects/",
]

try:
    data = json.load(sys.stdin)
    fp = data.get("tool_input", {}).get("file_path", "")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

if not fp:
    sys.exit(0)

# Normalise to forward slashes for consistent matching
fp_norm = fp.replace("\\", "/")

# Check if path is inside the Projects/ parent
projects_prefix = None
for marker in PROJECTS_MARKERS:
    if fp_norm.startswith(marker.replace("\\", "/")):
        projects_prefix = marker.replace("\\", "/")
        break

if not projects_prefix:
    sys.exit(0)

# Extract the repo name (first path component after Projects/)
remainder = fp_norm[len(projects_prefix):]
repo = remainder.split("/")[0]

# Exclude the hub itself
if repo == HUB_NAME or not repo:
    sys.exit(0)

# Compute the CLAUDE.md path for display
claude_md = f"{projects_prefix}{repo}/CLAUDE.md"

print(
    f"[SIBLING EDIT] Editing {repo} — read its CLAUDE.md first if you haven't:\n"
    f"  {claude_md}"
)
sys.exit(0)
