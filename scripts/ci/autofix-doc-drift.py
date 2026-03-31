#!/usr/bin/env python3
"""Auto-fix stale kr-forensic-finance references in hub files.

Reads _scratchpad/doc-drift.json (produced by doc-drift-scan.sh).
Applies text replacement for findings whose file path is inside the hub
workspace root. Sibling repo findings are reported but not touched — they
require per-repo write access that the default GITHUB_TOKEN doesn't cover.

Exit codes:
  0 — one or more hub files fixed and written
  1 — input file missing or unreadable
  2 — no fixable findings (zero findings, or all in sibling repos)
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

workspace = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
drift_path = workspace / "_scratchpad" / "doc-drift.json"

if not drift_path.exists():
    print("ERROR: _scratchpad/doc-drift.json not found", file=sys.stderr)
    sys.exit(1)

data = json.loads(drift_path.read_text(encoding="utf-8"))
findings = data.get("findings", [])

if not findings:
    print("No drift findings — nothing to fix.")
    sys.exit(2)

# Split into hub-local vs sibling
hub_findings: list[dict] = []
sibling_findings: list[dict] = []
for f in findings:
    filepath = Path(f["file"]).resolve()
    try:
        filepath.relative_to(workspace)
        hub_findings.append(f)
    except ValueError:
        sibling_findings.append(f)

if sibling_findings:
    repos = {f.get("repo", "?") for f in sibling_findings}
    print(f"Note: {len(sibling_findings)} finding(s) in sibling repos ({', '.join(sorted(repos))}) — require per-repo PAT to auto-fix.")

if not hub_findings:
    print("No hub-local findings — skipping autofix.")
    sys.exit(2)

# Group by file path and apply replacement
by_file: dict[str, list] = defaultdict(list)
for f in hub_findings:
    by_file[f["file"]].append(f)

fixed_files: list[str] = []
for filepath_str in by_file:
    p = Path(filepath_str)
    if not p.exists():
        print(f"  SKIP (not found): {filepath_str}")
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    new_text = text.replace("kr-forensic-finance", "forensic-accounting-toolkit")
    if new_text != text:
        p.write_text(new_text, encoding="utf-8")
        fixed_files.append(str(p))
        print(f"  Fixed: {p}")
    else:
        print(f"  SKIP (no plain text match, may be in excluded context): {p}")

if not fixed_files:
    print("No hub files changed.")
    sys.exit(2)

print(f"Fixed {len(fixed_files)} hub file(s).")
sys.exit(0)
