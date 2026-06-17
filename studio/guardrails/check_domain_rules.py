#!/usr/bin/env python3
"""Forensic Studio domain guardrail (Gate 0, deterministic, bypass-proof).

Hard rule enforced here: **data/raw/ is immutable.** Exits non-zero if any changed
file in the given git range lives under a `data/raw/` directory in any repo. Runs in
CI on every maintenance PR so an autonomous agent's *own diff* trips it — it cannot be
talked around by a prompt.

(Other hard rules — K-GAAP/IFRS separation, split-adjustment, M-score calibration,
"probability not verdict" — are enforced as tests inside their own repos; this central
check guards the one rule that is purely path-based and ecosystem-wide.)

Usage:
    python studio/guardrails/check_domain_rules.py [--base REF] [--head REF]
    python studio/guardrails/check_domain_rules.py --paths a/b.py data/raw/x.csv   # explicit
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

RAW_RE = re.compile(r"(^|/)data/raw/")


def changed_paths(base: str, head: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}...{head}"], text=True
    )
    return [p.strip() for p in out.splitlines() if p.strip()]


def violations(paths: list[str]) -> list[str]:
    return [p for p in paths if RAW_RE.search(p.replace("\\", "/"))]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--paths", nargs="*", help="explicit paths (skips git diff)")
    args = ap.parse_args(argv)

    paths = args.paths if args.paths is not None else changed_paths(args.base, args.head)
    bad = violations(paths)
    if bad:
        print("DOMAIN GUARDRAIL VIOLATION — data/raw/ is immutable.", file=sys.stderr)
        for p in bad:
            print(f"  offending: {p}", file=sys.stderr)
        return 1
    print(f"domain guardrail OK — {len(paths)} changed path(s), no data/raw/ writes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
