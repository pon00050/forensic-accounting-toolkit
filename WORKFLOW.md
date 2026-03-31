# Workflow Manual

Practical command sequences for common operations in the forensic accounting ecosystem. All commands assume you're in the hub directory (`C:\Users\pon00\Projects\forensic-accounting-toolkit`) unless noted otherwise.

---

## 1. Starting a Session

Session auto-runs a quick triage (board + git hygiene + backlog) via the session-start hook.

```bash
# For full scan across all 10 sources (board, git, data, code signals, conventions, etc.)
/triage

# For board detail with wave scheduling
/board

# For strategic 5-layer ecosystem analysis
/plan
```

If triage surfaces immediate items (uncommitted changes, stale data), address those first.
Otherwise, pick the recommended task and go to section 2 or 3.

---

## 2. Working on a Specific Repo

```bash
# Switch context to the repo (loads CLAUDE.md, shows git status, runs tests)
/work kr-beneish
```

Then do your work — edit code, run tests, commit. When done:

```bash
# From the repo directory:
git add <files>
git commit -m "feat: description of change"
git push

# Back in the hub, mark it done on the board:
/done <task-title>
```

`/done` handles: board update, CHANGELOG entry, ECOSYSTEM.md check, content assessment.

---

## 3. Running the Issuance Dilution Screen (kr-derivatives)

This is the most common multi-repo workflow. It spans kr-dart-pipeline (ETL) and kr-derivatives (screen).

### 3a. If pipeline data changed (new extraction)

```bash
# In kr-dart-pipeline — run the extractor that changed
cd /c/Users/pon00/Projects/kr-dart-pipeline
uv run python kr_dart_pipeline/extract_price_volume.py      # or whichever extractor
uv run python kr_dart_pipeline/extract_corp_actions.py       # if corporate actions changed

# Sync outputs to kr-derivatives
cd /c/Users/pon00/Projects/forensic-accounting-toolkit
bash ecosystem.sh copy-parquets
```

This copies `price_volume.parquet`, `cb_bw_events.parquet`, and `corp_actions.parquet` from krff-shell's output to kr-derivatives' input.

### 3b. Run the screen

```bash
cd /c/Users/pon00/Projects/kr-derivatives
uv run python examples/02_issuance_dilution_screen.py
```

### 3c. Inspect results

```python
# In the kr-derivatives directory:
uv run python -c "
import pandas as pd
df = pd.read_csv('issuance_dilution_scores.csv')
print('Flag rate:', df['dilution_flag'].mean())
print('Moneyness >10x:', (df['moneyness'] > 10).sum())
print('Moneyness >5x:', (df['moneyness'] > 5).sum())
print('Rows:', len(df))
"
```

For the full inspection protocol, see `kr-derivatives/reports/README.md` § Standard Inspection Queries.

### 3d. Document the run

Write `reports/{n}_run_lessons.md` following the template in `reports/README.md`. Then:

```bash
cd /c/Users/pon00/Projects/kr-derivatives
git add issuance_dilution_scores.csv reports/
git commit -m "feat: Run N — description of changes and results"
git push
```

### 3e. If outliers show moneyness >10x

```bash
# Back in the hub
/diagnose-moneyness
```

This queries DART for CB filings and corporate actions, checks adjusted vs unadjusted prices, and classifies each case.

---

## 4. Running Tests

```bash
# All repos at once (from the hub):
bash ecosystem.sh test-all

# One specific repo:
bash ecosystem.sh test kr-beneish

# Or directly in a repo:
cd /c/Users/pon00/Projects/kr-beneish
uv run pytest tests/ -v
```

Test commands per repo:

| Repo | Command |
|------|---------|
| krff-shell | `uv run pytest tests/ -v` |
| kr-forensic-core | `uv run pytest tests/ -v` |
| kr-dart-pipeline | `uv run pytest tests/ -v` |
| kr-anomaly-scoring | `uv run pytest tests/ -v` |
| kr-stat-tests | `uv run pytest tests/ -v` |
| kr-beneish | `uv run pytest tests/ -v` |
| kr-derivatives | `uv run pytest tests/ -v` |
| kr-trading-calendar | `uv run pytest tests/ -v` |
| jfia-forensic | `uv run pytest tests/ -v` |
| kr-enforcement-cases | `uv run pytest tests/ -v` |
| kr-company-registry | `pytest tests/ -v` |
| jfia-catalog | (no tests) |

---

## 5. Ending a Session

```bash
/session-end
```

This runs a read-only audit:
- Uncommitted/unpushed changes across all repos
- Stale board items
- CHANGELOG freshness
- Uncaptured content worth recording

If it flags issues, address them or note them for next time. It won't fix anything on its own.

---

## 6. Content Capture

When you've done something worth writing about (debugging story, API discovery, metric improvement):

```bash
# Capture it
/capture denomination-mismatch-fix

# Review what's been captured
/content
```

`/done` will also suggest captures when the completed task matches content-worthy patterns. You decide whether to act on it.

---

## 7. Cross-Repo Dependency Upgrade

Example: upgrading pykrx across the ecosystem.

```bash
# 1. Make the change in the source repo
cd /c/Users/pon00/Projects/kr-dart-pipeline
# Edit pyproject.toml
uv lock && uv sync

# 2. Run tests in the changed repo
uv run pytest tests/ -v

# 3. If pipeline outputs changed, sync downstream
cd /c/Users/pon00/Projects/forensic-accounting-toolkit
bash ecosystem.sh copy-parquets

# 4. Run tests in downstream repos
bash ecosystem.sh test kr-derivatives

# 5. If everything passes, commit and push both
cd /c/Users/pon00/Projects/kr-dart-pipeline
git add pyproject.toml uv.lock
git commit -m "chore: upgrade pykrx to X.Y.Z"
git push

cd /c/Users/pon00/Projects/kr-derivatives
# (only if data files changed)
git add data/input/
git commit -m "chore: sync input parquets after pykrx upgrade"
git push

# 6. Verify nothing left behind
cd /c/Users/pon00/Projects/forensic-accounting-toolkit
bash ecosystem.sh unpushed
```

---

## 8. Convention Audit

After changes across multiple repos, verify everything still follows the canonical conventions:

```bash
/plan conventions
```

This launches the convention-auditor agent to check all repos against the checklist in `.claude/skills/canonical-conventions/SKILL.md`.

---

## 9. Board Management

```bash
# View the board
/board

# Mark a task done (includes CHANGELOG, ECOSYSTEM.md, content assessment)
/done <task-title>

# Check ecosystem publication and blocker status
/ecosystem-status
```

The board lives on GitHub Projects. Direct CLI access:

```bash
"/c/Program Files/GitHub CLI/gh.exe" project item-list 1 --owner pon00050 --format json
```

---

## Quick Reference

| I want to... | Command |
|---------------|---------|
| Full task scan | `/triage` |
| See what to work on | `/board` |
| Switch to a repo | `/work <repo>` |
| Run all tests | `bash ecosystem.sh test-all` |
| Sync parquets downstream | `bash ecosystem.sh copy-parquets` |
| Check git status everywhere | `bash ecosystem.sh status` |
| Check unpushed commits | `bash ecosystem.sh unpushed` |
| Mark a task complete | `/done <title>` |
| Run the dilution screen | `uv run python examples/02_issuance_dilution_screen.py` |
| Diagnose extreme moneyness | `/diagnose-moneyness` |
| Capture content | `/capture <title>` |
| Review content pipeline | `/content` |
| Audit conventions | `/plan conventions` |
| End the session | `/session-end` |
