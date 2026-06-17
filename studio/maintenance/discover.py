#!/usr/bin/env python3
"""Studio maintenance discovery (deterministic).

Reads the refinement backlog + the fleet config and writes a dated discovery report: the
work the maintenance crew would queue, classified by autonomy-safety, with each item marked
auto-mergeable or propose-only per the fleet config's `auto_merge_classes`. No code changes,
no LLM. In full mode the same backlog feeds one-agent-per-item execution (Phase 3, not yet built).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import yaml


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def render(backlog: dict, config: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    posture = config.get("posture", "unknown")
    auto_classes = set(config.get("auto_merge_classes", []))
    items = backlog.get("items", [])
    open_items = [i for i in items if i.get("status", "open") == "open"]
    safe = [i for i in open_items if i.get("safety") == "SAFE"]
    lines = [
        f"# Studio maintenance discovery — {ts}",
        "",
        f"Posture: **{posture}**. {len(open_items)} open of {len(items)} item(s); {len(safe)} SAFE. "
        "Items whose class is in the fleet auto-merge whitelist are eligible for autonomous "
        "fix→verify→auto-merge (Phase 3, not yet built); all others are propose-only.",
        "",
        "| id | class | safety | auto-merge? | repo | summary |",
        "|---|---|---|---|---|---|",
    ]
    for i in open_items:
        am = "yes" if (i.get("safety") == "SAFE" and i.get("class") in auto_classes) else "no"
        lines.append(
            f"| {i.get('id', '?')} | {i.get('class', '?')} | {i.get('safety', '?')} | {am} "
            f"| {i.get('repo', '?')} | {i.get('summary', '')} |"
        )
    lines += ["", "_machine-generated, unreviewed — discovery only, no changes made._", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backlog", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=Path("studio/fleet.config.yml"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    config = _load_yaml(args.config) if args.config.exists() else {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(_load_yaml(args.backlog), config), encoding="utf-8")
    print(f"discovery report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
