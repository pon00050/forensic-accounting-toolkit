# Studio maintenance discovery — 2026-06-17T09:04:14+00:00

8 open item(s) of 8 total; 6 are SAFE (eligible for autonomous fix→verify→auto-merge). NEEDS-REVIEW / HUMAN-ONLY items are proposed only, never auto-merged.

| id | class | safety | repo | summary |
|---|---|---|---|---|
| TEST-stat | test-addition | SAFE | kr-stat-tests | Synthetic fixture parquets + behavioral tests for the 14 stat scripts (3.4k LOC, only 5 tests today). |
| TEST-dart | test-addition | SAFE | kr-dart-pipeline | Tests for the 15 extractors + transform.py (currently untested). |
| TEST-enf | test-addition | SAFE | kr-enforcement-cases | Fixture parquets to lift coverage beyond '65 tests for 19 modules'. |
| TYPES-core | type-hints | SAFE | kr-forensic-core | Type hints + docstrings on the shared foundation (9% return-hint coverage). |
| LINT-eco | lint-fix | SAFE | all | Add ruff+mypy config ecosystem-wide (8/12 repos lack it); ruff --fix. |
| DOC-enf-count | doc-count-sync | SAFE | kr-enforcement-cases | README says violations.csv=240; actual ~6,235. Regenerate counts from files. |
| DEDUP-krff | refactor | NEEDS-REVIEW | krff-shell | 02_Pipeline/03_Analysis hold ~9.7k LOC of diverged ETL copies; de-dup needs test refactor + sign-off. |
| SEIBRO | data-source | HUMAN-ONLY | kr-dart-pipeline | SEIBRO/XB-002 external API; re-check whether live (April ETA passed) before any work. |

_machine-generated, unreviewed — discovery only, no changes made._
