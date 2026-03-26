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
    fp = data.get("tool_input", {}).get("file_path", "")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

if not fp:
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
    if "`kr-forensic-finance`" in line or '"kr-forensic-finance"' in line:
        continue
    hits.append((i, line.strip()))
    if len(hits) == 4:
        break  # display cap reached; no need to scan further

if not hits:
    sys.exit(0)

print(f"[DOC DRIFT] Stale name 'kr-forensic-finance' in {fp}:")
for lineno, text in hits:
    print(f"  line {lineno}: {text[:100]}")
print("  Replace with 'krff-shell' (delivery shell) or 'kr-dart-pipeline' (ETL) as appropriate.")

sys.exit(0)
