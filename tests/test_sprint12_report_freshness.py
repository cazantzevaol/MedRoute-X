from scripts.submission_gate import reported_test_count, inspect_pdf
from pathlib import Path


def test_count_extracted():
    assert reported_test_count("Offline regression suite: 199 tests in build") == 199

def test_missing_count_rejected():
    assert reported_test_count("We tested the application") is None

def test_ambiguous_count_rejected():
    assert reported_test_count("Offline regression suite: 199 tests. Offline regression suite: 172 tests.") is None

def test_current_report_matches_suite():
    root = Path(__file__).resolve().parents[1]
    pages, issues = inspect_pdf(root / "reports" / "technical_report.pdf", "0.10", expected_tests=376)
    assert pages == 5
    assert issues == []
