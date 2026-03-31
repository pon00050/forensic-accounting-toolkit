#!/usr/bin/env python3
"""Auto-fix stale kr-forensic-finance references.

Reads _scratchpad/doc-drift.json (produced by doc-drift-scan.sh).

Hub files (inside $GITHUB_WORKSPACE): fixed directly and written.
Sibling repo files: written to _scratchpad/sibling-drift.json for the
workflow's PAT-based push step to handle.

Exit codes:
  0 — one or more hub files fixed and written
  1 — input file missing or unreadable
  2 — no fixable hub findings (zero count, or all in sibling repos)
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

# Always write sibling-drift.json so the bash step can pick it up
sibling_by_repo: dict[str, list[str]] = defaultdict(list)
hub_findings: list[dict] = []

for f in findings:
    filepath = Path(f["file"])
    try:
        filepath.resolve().relative_to(workspace)
        hub_findings.append(f)
    except ValueError:
        sibling_by_repo[f.get("repo", "unknown")].append(f["file"])

sibling_output = {
    "repo_count": len(sibling_by_repo),
    "repos": {repo: sorted(set(files)) for repo, files in sibling_by_repo.items()},
}
(workspace / "_scratchpad" / "sibling-drift.json").write_text(
    json.dumps(sibling_output, indent=2), encoding="utf-8"
)

if sibling_by_repo:
    repos = sorted(sibling_by_repo)
    print(f"Note: {sum(len(v) for v in sibling_by_repo.values())} sibling finding(s) "
          f"in {repos} written to sibling-drift.json for PAT-based push step.")

if not findings:
    print("No drift findings — nothing to fix.")
    sys.exit(2)

if not hub_findings:
    print("No hub-local findings — skipping hub autofix.")
    sys.exit(2)

# Group hub findings by file path
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
        print(f"  SKIP (no plain-text match): {p}")

if not fixed_files:
    print("No hub files changed.")
    sys.exit(2)

print(f"Fixed {len(fixed_files)} hub file(s).")
sys.exit(0)
