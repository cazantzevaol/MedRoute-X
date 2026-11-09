"""Release-metadata consistency; never asserts legal or external submission approval."""
from pathlib import Path
from scripts.submission_gate import audit_submission, inspect_pdf

ROOT = Path(__file__).resolve().parents[1]


def test_release_pdf_matches_verified_suite():
    pages, issues = inspect_pdf(ROOT / 'reports' / 'technical_report.pdf', '0.10', 376)
    assert pages == 5
    assert not issues


def test_release_kb_counts_match_verified_fixture():
    result = audit_submission(ROOT, expected_tests=376, expected_sources=14, expected_claims=18)
    assert result['local_preflight_passed']
    assert not result['submission_ready']


def test_stale_test_count_fails_closed():
    result = audit_submission(ROOT, expected_tests=199)
    assert not result['local_preflight_passed']
    assert any('test count' in issue for issue in result['issues'])


def test_stale_source_count_fails_closed():
    result = audit_submission(ROOT, expected_sources=13)
    assert not result['local_preflight_passed']
    assert any('source count' in issue for issue in result['issues'])


def test_stale_claim_count_fails_closed():
    result = audit_submission(ROOT, expected_claims=17)
    assert not result['local_preflight_passed']
    assert any('claim count' in issue for issue in result['issues'])
