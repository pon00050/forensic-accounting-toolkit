#!/usr/bin/env python3
"""PostToolUse hook: catch stale repo-name references at the moment of introduction.

Fires after Edit or Write tool calls. Reads the modified file and warns if
'kr-forensic-finance' appears in non-historical lines. Claude sees the warning
and can fix it immediately, before the stale name is committed.
"""
import json
import sys

try:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input", {})
    fp = tool_input.get("file_path", "")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

if not fp:
    sys.exit(0)

# Only check documentation files — skip parquets, binaries, etc.
if not any(fp.endswith(ext) for ext in (".md", ".toml", ".conf", ".py", ".sh", ".txt", ".yaml", ".yml", ".json")):
    sys.exit(0)

try:
    with open(fp, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
except Exception:
    sys.exit(0)

# Collect lines with stale name, excluding known-good references:
# - "Previously known as" lines (historical rename notes)
# - Lines where the name is quoted as a search pattern (backtick or grep string)
hits = []
for i, line in enumerate(lines, 1):
    if "kr-forensic-finance" not in line:
        continue
    if "Previously known as" in line:
        continue
    # Skip lines where it appears as a quoted code/grep pattern (meta-reference)
    if "`kr-forensic-finance`" in line or '"kr-forensic-finance"' in line:
        continue
    hits.append((i, line.strip()))

if not hits:
    sys.exit(0)

print(f"[DOC DRIFT] Stale name 'kr-forensic-finance' in {fp}:")
for lineno, text in hits[:4]:
    print(f"  line {lineno}: {text[:100]}")
if len(hits) > 4:
    print(f"  ... and {len(hits) - 4} more")
print("  Replace with 'krff-shell' (delivery shell) or 'kr-dart-pipeline' (ETL) as appropriate.")

sys.exit(0)
