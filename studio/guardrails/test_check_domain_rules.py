"""Tests for the data/raw immutability guardrail."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_domain_rules as g  # noqa: E402

violations = g.violations


def test_flags_data_raw():
    assert violations(["src/x.py", "data/raw/dart/a.json"]) == ["data/raw/dart/a.json"]


def test_allows_normal_paths():
    assert violations(["src/x.py", "reports/out.csv", "data/processed/y.parquet"]) == []


def test_flags_nested_repo_data_raw():
    p = "_deps/kr-dart-pipeline/data/raw/z.csv"
    assert violations([p]) == [p]


def test_allows_data_raw_substring_not_dir():
    # "data_raw_notes.md" is not the immutable dir; must not be flagged.
    assert violations(["docs/data_raw_notes.md"]) == []
