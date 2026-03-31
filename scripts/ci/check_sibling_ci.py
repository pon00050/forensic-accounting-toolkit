#!/usr/bin/env python3
"""
Poll check-run status for the master HEAD of every sibling repo.

Uses the GitHub Checks API: GET /repos/{owner}/{repo}/commits/{ref}/check-runs
This returns check runs for the *current* HEAD of master — so it reflects the
live state of the branch, not a time-windowed history scan.

Writes _scratchpad/sibling-ci-failures.json:
  {
    "failures": [{repo, check_name, conclusion, html_url, completed_at}],
    "checked_at": "<ISO-8601>"
  }

Requires ECOSYSTEM_PAT with 'repo' scope on all sibling repos.
Falls back gracefully (warning, not error) when PAT is missing or repo is inaccessible.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPOS = [
    "kr-company-registry",
    "kr-trading-calendar",
    "kr-beneish",
    "kr-derivatives",
    "jfia-forensic",
    "kr-enforcement-cases",
    "kr-forensic-core",
    "kr-dart-pipeline",
    "kr-anomaly-scoring",
    "kr-stat-tests",
    "krff-shell",
]

# Conclusions that mean the check is broken on master right now.
FAILING_CONCLUSIONS = {"failure", "timed_out", "startup_failure"}

# Conclusions we actively ignore (these don't mean the branch is broken).
BENIGN_CONCLUSIONS = {"success", "neutral", "skipped", "cancelled", "action_required"}


def check_repo(repo: str) -> list[dict]:
    """Return failing check-runs for repo's master HEAD. Returns [] if repo is inaccessible."""
    result = subprocess.run(
        [
            "gh", "api",
            f"repos/pon00050/{repo}/commits/master/check-runs",
            "--jq",
            (
                ".check_runs[] | "
                "select(.status == \"completed\") | "
                "{check_name: .name, conclusion: .conclusion, "
                "html_url: .html_url, completed_at: .completed_at, "
                "app: .app.slug}"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )

    if result.returncode != 0:
        # 404 = repo inaccessible (PAT missing or private); warn but don't fail the run
        stderr = result.stderr.strip()
        if "Not Found" in stderr or "HTTP 404" in stderr:
            print(f"  SKIP {repo}: inaccessible (ECOSYSTEM_PAT may not cover this repo)")
        else:
            print(f"  WARN {repo}: API error — {stderr[:120]}")
        return []

    failures = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            check = json.loads(line)
        except json.JSONDecodeError:
            continue
        if check.get("conclusion") in FAILING_CONCLUSIONS:
            check["repo"] = repo
            failures.append(check)

    return failures


def main() -> None:
    scratchpad = Path(os.environ.get("GITHUB_WORKSPACE", ".")) / "_scratchpad"
    scratchpad.mkdir(exist_ok=True)

    all_failures: list[dict] = []
    checked_at = datetime.now(timezone.utc).isoformat()

    for repo in REPOS:
        try:
            failures = check_repo(repo)
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT {repo} — skipping")
            continue
        except Exception as e:
            print(f"  ERR {repo}: {e}")
            continue

        if failures:
            print(f"  FAIL {repo}: {len(failures)} failing check(s) on master")
            for f in failures:
                print(f"       └ {f['check_name']} ({f['conclusion']})")
            all_failures.extend(failures)
        else:
            print(f"  OK   {repo}")

    output = {
        "failures": all_failures,
        "checked_at": checked_at,
        "repos_checked": len(REPOS),
    }
    (scratchpad / "sibling-ci-failures.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )

    if all_failures:
        failed_repos = {f["repo"] for f in all_failures}
        print(f"\n{len(all_failures)} failing check(s) across {len(failed_repos)} repo(s): {', '.join(sorted(failed_repos))}")
        sys.exit(0)   # non-zero would fail the workflow step; issue creation handles alerting
    else:
        print(f"\nAll {len(REPOS)} sibling repos: master CI green")


if __name__ == "__main__":
    main()
