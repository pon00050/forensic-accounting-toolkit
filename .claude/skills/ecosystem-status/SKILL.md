---
name: ecosystem-status
description: Health check across all 14 ecosystem repos — uncommitted changes, test status, remote sync
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash
---

Scan all ecosystem repos and report their health. This is a read-only diagnostic.

**Note:** `bash ecosystem.sh status` does the same thing faster from the hub. Use this skill when you want the AI to interpret and summarize the results.

## Repos to check

All paths relative to `C:\Users\pon00\Projects\`:

1. forensic-accounting-toolkit (hub — no tests)
2. kr-company-registry
3. kr-trading-calendar
4. kr-beneish
5. jfia-catalog (no tests)
6. kr-derivatives
7. jfia-forensic
8. kr-enforcement-cases
9. kr-forensic-core
10. kr-dart-pipeline
11. kr-anomaly-scoring
12. kr-stat-tests
13. krff-shell
14. kr-real-estate (no tests)

## For each repo, check

Run these checks in parallel where possible:

1. **Git status**: `git status --short` — count uncommitted changes
2. **Remote sync**: `git log --oneline @{upstream}..HEAD 2>/dev/null` — commits not pushed
3. **Branch**: `git branch --show-current`

Do NOT run tests here (use the ecosystem-test-runner agent for that).

## Output format

Display a table:

```
Repo                     Branch   Uncommitted   Unpushed
forensic-accounting-toolkit  master   0            0
kr-forensic-finance      master   2            0
...
```

Flag any repo with uncommitted changes or unpushed commits with a warning marker.

End with a one-line summary: "X repos clean, Y need attention."

## Rules

- Read-only. Do not modify any files or make commits.
- Do not run tests (that's what the ecosystem-test-runner agent is for).
- If a repo is missing or not a git repo, note it and continue.
