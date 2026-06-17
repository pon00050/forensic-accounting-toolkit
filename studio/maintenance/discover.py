#!/usr/bin/env python3
"""Studio maintenance discovery (deterministic).

Reads the refinement backlog and writes a dated discovery report: the work the
maintenance crew would queue, classified by autonomy-safety. No code changes, no LLM.
In full mode the same backlog feeds one-agent-per-item execution (Phase 3).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_backlog(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def render(backlog: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    items = backlog.get("items", [])
    open_items = [i for i in items if i.get("status", "open") == "open"]
    safe = [i for i in open_items if i.get("safety") == "SAFE"]
    lines = [
        f"# Studio maintenance discovery — {ts}",
        "",
        f"{len(open_items)} open item(s) of {len(items)} total; {len(safe)} are SAFE "
        "(eligible for autonomous fix→verify→auto-merge). NEEDS-REVIEW / HUMAN-ONLY "
        "items are proposed only, never auto-merged.",
        "",
        "| id | class | safety | repo | summary |",
        "|---|---|---|---|---|",
    ]
    for i in open_items:
        lines.append(
            f"| {i.get('id', '?')} | {i.get('class', '?')} | {i.get('safety', '?')} "
            f"| {i.get('repo', '?')} | {i.get('summary', '')} |"
        )
    lines += ["", "_machine-generated, unreviewed — discovery only, no changes made._", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backlog", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(load_backlog(args.backlog)), encoding="utf-8")
    print(f"discovery report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
