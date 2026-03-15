---
name: canonical-conventions
description: Canonical conventions for the forensic accounting ecosystem — preloaded into convention-auditor agent as the single source of truth for convention checks.
user-invocable: false
---

# Canonical Conventions

This is the authoritative convention table for the Korean forensic accounting ecosystem. The convention-auditor agent uses this to check all repos for deviations.

## Convention Checklist

| # | Convention | Expected | Check Method | Exceptions |
|---|-----------|----------|-------------|------------|
| 1 | Build system | `hatchling` (`requires = ["hatchling"]` in `[build-system]`) | `grep build-backend pyproject.toml` | jfia-catalog (data artifact, no build system required) |
| 2 | Python version | `>=3.11` in `[project] requires-python` | `grep requires-python pyproject.toml` | kr-beneish: `>=3.10` is acceptable |
| 3 | Package manager | `uv` (never pip) | Check CLAUDE.md mentions uv; no `requirements.txt` present | — |
| 4 | Test invocation | `uv run pytest tests/ -v` | Check CLAUDE.md for test command | kr-forensic-finance: `python -m pytest` is acceptable |
| 5 | uv.lock committed | File tracked in git | `git -C <repo> ls-files uv.lock` | jfia-catalog (no dependencies) |
| 6 | conftest.py present | Required in repos that have a `tests/` directory | `test -f tests/conftest.py` | Repos without tests/ are exempt |
| 7 | constants.py present | Required in repos with magic strings/thresholds in code | Check for `src/*/constants.py` or `src/constants.py` | kr-trading-calendar (no magic strings beyond holiday list) |
| 8 | Paths module | `_paths.py` or `paths.py` in src | `find src/ -name '*paths*'` | Repos with no file I/O are exempt |
| 9 | Commit message style | Conventional prefix: feat/fix/docs/refactor/test/chore | `git log --oneline -5` | — |
| 10 | .claude/ directory | Present at repo root | `test -d .claude` | jfia-catalog (minimal repo) |
| 11 | compile-bytecode | `compile-bytecode = false` in `[tool.uv]` | `grep compile-bytecode pyproject.toml` | Repos without pyproject.toml |
| 12 | CLAUDE.md present | Present at repo root | `test -f CLAUDE.md` | — |

## Severity Levels

- **DRIFT**: Convention exists but deviates from expected value (e.g., wrong build system)
- **MISS**: Convention artifact is completely absent (e.g., no conftest.py)
- **OK**: Matches expected convention
- **EXEMPT**: Repo has a documented exception for this convention

## Repos to Audit

All repos under `C:\Users\pon00\Projects\`:

1. `kr-forensic-finance`
2. `kr-company-registry`
3. `kr-beneish`
4. `kr-derivatives`
5. `kr-trading-calendar`
6. `jfia-catalog`
7. `jfia-forensic`
8. `kr-real-estate`
