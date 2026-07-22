# Studio maintenance discovery — 2026-07-22T23:09:36+00:00

Posture: **internal-only**. 8 open of 8 item(s); 6 SAFE. Items whose class is in the fleet auto-merge whitelist are eligible for autonomous fix→verify→auto-merge (Phase 3, not yet built); all others are propose-only.

| id | class | safety | auto-merge? | repo | summary |
|---|---|---|---|---|---|
| TEST-stat | test-addition | SAFE | yes | kr-stat-tests | Synthetic fixture parquets + behavioral tests for the 14 stat scripts (3.4k LOC, only 5 tests today). |
| TEST-dart | test-addition | SAFE | yes | kr-dart-pipeline | Tests for the 15 extractors + transform.py (currently untested). |
| TEST-enf | test-addition | SAFE | yes | kr-enforcement-cases | Fixture parquets to lift coverage beyond '65 tests for 19 modules'. |
| TYPES-core | type-hints | SAFE | yes | kr-forensic-core | Type hints + docstrings on the shared foundation (9% return-hint coverage). |
| LINT-eco | lint-fix | SAFE | yes | all | Add ruff+mypy config ecosystem-wide (8/12 repos lack it); ruff --fix. |
| DOC-enf-count | doc-count-sync | SAFE | yes | kr-enforcement-cases | README says violations.csv=240; actual ~6,235. Regenerate counts from files. |
| DEDUP-krff | refactor | NEEDS-REVIEW | no | krff-shell | 02_Pipeline/03_Analysis hold ~9.7k LOC of diverged ETL copies; de-dup needs test refactor + sign-off. |
| SEIBRO | data-source | HUMAN-ONLY | no | kr-dart-pipeline | SEIBRO/XB-002 external API; re-check whether live (April ETA passed) before any work. |

_machine-generated, unreviewed — discovery only, no changes made._
