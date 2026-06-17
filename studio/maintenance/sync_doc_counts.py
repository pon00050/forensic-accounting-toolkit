#!/usr/bin/env python3
"""Studio maintenance engine: reconcile ECOSYSTEM.md test counts to the authoritative
source (hub CLAUDE.md ecosystem tables). Deterministic — no LLM, no secrets.

Project convention (CLAUDE.md "Documentation Maintenance"): test counts live in the hub
CLAUDE.md ecosystem table; ECOSYSTEM.md's publication table must match. This engine fixes
drift (e.g. a stale "N tests") by rewriting only the number before " tests" on the
ECOSYSTEM.md row for each repo whose authoritative count differs. It never invents a count
for a repo that has none in ECOSYSTEM.md, and never touches CLAUDE.md (the source of truth).

Usage:
    python studio/maintenance/sync_doc_counts.py            # apply fixes, print changes
    python studio/maintenance/sync_doc_counts.py --check    # report only; exit 1 if drift
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_MD = ROOT / "CLAUDE.md"
ECOSYSTEM_MD = ROOT / "ECOSYSTEM.md"

# Authoritative count rows in CLAUDE.md look like:
#   | **kr-beneish** | `../kr-beneish` | Beneish M-Score ... | 73 |
_CLAUDE_ROW = re.compile(r"^\|\s*\*\*([a-z0-9][a-z0-9-]+)\*\*\s*\|.*\|\s*(\d+)\s*\|\s*$")
_TESTS = re.compile(r"\b(\d+)\s+tests\b")


def authoritative_counts(claude_text: str) -> dict[str, int]:
    """Map repo -> test count from the CLAUDE.md ecosystem tables."""
    counts: dict[str, int] = {}
    for line in claude_text.splitlines():
        m = _CLAUDE_ROW.match(line)
        if m:
            counts[m.group(1)] = int(m.group(2))
    return counts


def reconcile(ecosystem_text: str, counts: dict[str, int]) -> tuple[str, list[str]]:
    """Return (new_text, changes). Only rewrites 'N tests' on a row that names a known
    repo and whose stated count differs from the authoritative one."""
    changes: list[str] = []
    lines = ecosystem_text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = _TESTS.search(line)
        if not m:
            continue
        repo = next(
            (r for r in counts if re.search(rf"(?<![\w-]){re.escape(r)}(?![\w-])", line)),
            None,
        )
        if repo is None:
            continue
        old = int(m.group(1))
        if old != counts[repo]:
            lines[i] = _TESTS.sub(f"{counts[repo]} tests", line, count=1)
            changes.append(f"{repo}: {old} -> {counts[repo]} tests")
    return "".join(lines), changes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if drift found")
    args = ap.parse_args(argv)

    counts = authoritative_counts(CLAUDE_MD.read_text(encoding="utf-8"))
    if not counts:
        print("WARN: no authoritative counts parsed from CLAUDE.md; doing nothing", file=sys.stderr)
        return 0
    new_text, changes = reconcile(ECOSYSTEM_MD.read_text(encoding="utf-8"), counts)

    if not changes:
        print("doc-count-sync: ECOSYSTEM.md already matches CLAUDE.md (no drift)")
        return 0

    if args.check:
        print("doc-count-sync: drift found:")
        for c in changes:
            print(f"  {c}")
        return 1

    ECOSYSTEM_MD.write_text(new_text, encoding="utf-8")
    print("doc-count-sync: applied:")
    for c in changes:
        print(f"  {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
