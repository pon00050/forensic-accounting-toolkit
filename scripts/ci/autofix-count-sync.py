#!/usr/bin/env python3
"""Auto-fix test count mismatches in hub CLAUDE.md.

Reads _scratchpad/count-sync.json (produced by count-sync-check.sh).
For each mismatch where actual > 0, updates the count column in CLAUDE.md.

Exit codes:
  0 — one or more counts fixed and written
  1 — input file missing or unreadable
  2 — no fixable mismatches (all collection failures or already in sync)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
sync_path = workspace / "_scratchpad" / "count-sync.json"

if not sync_path.exists():
    print("ERROR: _scratchpad/count-sync.json not found", file=sys.stderr)
    sys.exit(1)

data = json.loads(sync_path.read_text(encoding="utf-8"))
mismatches = data.get("mismatches", [])

if not mismatches:
    print("No mismatches — nothing to fix.")
    sys.exit(2)

# Only fix mismatches where actual > 0 (actual=0 means collection failure)
fixable = [m for m in mismatches if isinstance(m.get("actual"), int) and m["actual"] > 0]
if not fixable:
    print(f"All {len(mismatches)} mismatch(es) are collection failures — skipping autofix.")
    sys.exit(2)

claude_md = workspace / "CLAUDE.md"
if not claude_md.exists():
    print("ERROR: CLAUDE.md not found in workspace", file=sys.stderr)
    sys.exit(1)

content = claude_md.read_text(encoding="utf-8")
original = content
fixed_repos: list[str] = []

for m in fixable:
    repo = m["repo"]
    actual = int(m["actual"])
    # Match the table row: | **repo** | ... | <count> |
    # The count column is the last | N | on the row
    pattern = r'(\|\s*\*\*' + re.escape(repo) + r'\*\*\s*\|(?:[^|\n]*\|)*[^|\n]*\|\s*)(\d+)(\s*\|)'
    replaced, n = re.subn(
        pattern,
        lambda mo, a=actual: mo.group(1) + str(a) + mo.group(3),
        content,
    )
    if n > 0:
        content = replaced
        fixed_repos.append(f"  {repo}: {m['claimed']} → {actual}")
    else:
        print(f"  WARNING: pattern did not match row for '{repo}' in CLAUDE.md")

if content == original:
    print("No rows matched — CLAUDE.md unchanged.")
    sys.exit(2)

claude_md.write_text(content, encoding="utf-8")
print(f"Fixed {len(fixed_repos)} repo count(s) in CLAUDE.md:")
for line in fixed_repos:
    print(line)
sys.exit(0)
