#!/usr/bin/env python3
"""Forensic Studio provenance stamper.

Writes a machine-readable provenance manifest next to any autonomously generated
artifact. Internal-only posture: every artifact is labelled machine-generated and
unreviewed, with inputs hashed for reproducibility.

Usage:
    python studio/provenance.py stamp <artifact> [--model M] [--loop L] [--inputs f1 f2 ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DISCLAIMER = (
    "machine-generated, unreviewed — reproducible computation, not a verified claim "
    "or accusation. Report probability, not a verdict."
)


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def build_manifest(artifact: Path, model: str, loop: str, inputs: list[Path]) -> dict:
    return {
        "artifact": str(artifact).replace("\\", "/"),
        "artifact_sha256": _sha256(artifact),
        "generated_by": "forensic-studio",
        "loop": loop,
        "model": model,
        "git_sha": _git_sha(),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": [
            {"path": str(p).replace("\\", "/"), "sha256": _sha256(p)} for p in inputs
        ],
        "posture": "internal-only",
        "disclaimer": DISCLAIMER,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stamp", help="write <artifact>.provenance.json")
    s.add_argument("artifact", type=Path)
    s.add_argument("--model", default="none-deterministic")
    s.add_argument("--loop", default="unknown")
    s.add_argument("--inputs", nargs="*", type=Path, default=[])
    args = ap.parse_args(argv)

    manifest = build_manifest(args.artifact, args.model, args.loop, args.inputs)
    out = args.artifact.with_suffix(args.artifact.suffix + ".provenance.json")
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"provenance written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
