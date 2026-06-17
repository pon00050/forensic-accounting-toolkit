"""Tests for the deterministic doc-count-sync engine."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sync_doc_counts as s  # noqa: E402

CLAUDE = """\
| **kr-beneish** | `../kr-beneish` | Beneish M-Score for Korean IFRS companies | 73 |
| **krff-shell** | `../krff-shell` | Delivery shell | 317 |
| **kr-real-estate (portfolio)** | `../kr-real-estate` | Umbrella, no count column |
"""

ECOSYSTEM = """\
| kr-beneish | [x](u) | **Not published** | Published (2026-03-15). 61 tests. |
| krff-shell | pon00050/krff-shell | — | Published. 317 tests. SQL injection fixed. |
| jfia-catalog | [x](u) | — | Published (2026-03-15). Data artifact. |
"""


def test_authoritative_counts_parses_and_skips_no_count_rows():
    c = s.authoritative_counts(CLAUDE)
    assert c == {"kr-beneish": 73, "krff-shell": 317}


def test_reconcile_fixes_only_drifted_count():
    c = s.authoritative_counts(CLAUDE)
    new, changes = s.reconcile(ECOSYSTEM, c)
    assert changes == ["kr-beneish: 61 -> 73 tests"]
    assert "73 tests" in new and "61 tests" not in new
    assert new.count("317 tests") == 1          # unchanged, not duplicated
    assert "Data artifact" in new               # rows without 'N tests' untouched


def test_reconcile_noop_when_in_sync():
    c = {"kr-beneish": 61, "krff-shell": 317}
    new, changes = s.reconcile(ECOSYSTEM, c)
    assert changes == [] and new == ECOSYSTEM
