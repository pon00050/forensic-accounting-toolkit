#!/usr/bin/env python3
"""Claude Code PreToolUse hook: make data/raw/ physically un-writable by agents.

Blocks Edit/Write/MultiEdit/NotebookEdit whose target path is under a `data/raw/`
directory. Defense-in-depth alongside the CI guardrail (check_domain_rules.py).
Fails OPEN on any parse error (never breaks a session); the CI check is the hard gate.
"""
import json
import re
import sys

RAW_RE = re.compile(r"(^|[/\\])data[/\\]raw[/\\]")
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name", "") not in WRITE_TOOLS:
        return 0
    fp = (data.get("tool_input") or {}).get("file_path", "")
    if fp and RAW_RE.search(str(fp)):
        print(
            f"BLOCKED: data/raw/ is immutable (forensic hard rule). Refusing to write {fp}",
            file=sys.stderr,
        )
        return 2  # exit 2 = block the tool call in a Claude Code PreToolUse hook
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
