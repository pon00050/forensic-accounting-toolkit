# constraints.md — Forensic Toolkit Rules

## Data Integrity
- **Never modify raw DART/KRX data files.** `data/raw/` is immutable.
- **Never mix K-GAAP and K-IFRS numbers** in the same analysis. Always check the accounting standard.
- **Never extrapolate M-score** beyond the calibrated threshold. Report probability, not a verdict.
- **Split-adjustments must be applied** before any price-based ratio calculation. Use `kr-trading-calendar` for split dates.

## Code Quality
- **Always run tests before committing**: `pytest tests/ -q`. All 231+ tests must pass.
- **Never modify test files to make them pass.** Fix the source code.
- **Never hardcode ticker symbols or company names.** Use the constants module.
- **All DART API calls must go through the retry wrapper.** Never call the API directly.

## Triage System
- **Never duplicate triage-scan.sh logic** in move-forward skills. Call it as a subprocess and wrap output.
- **triage-last.json** is updated by triage-scan.sh. Do not edit it manually.
- **outreach-tracker.md** in `knowledge/business/` is the authoritative record for all client contacts.

## Publication Rules
- `kr-real-estate` has a two-repo structure (private code, public outputs). Not this project.
- All 6 repos are fully public. Never publish client-specific analysis to these repos.
- Version tags follow semver. `kr-enforcement-cases v1.0.0` is the current stable release.
