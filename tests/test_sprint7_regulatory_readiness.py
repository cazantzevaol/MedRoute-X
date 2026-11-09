"""Synthetic-only regression checks for legal review readiness."""
import json
from pathlib import Path
from scripts.submission_gate import audit_submission


def test_real_local_preflight_never_implies_legal_approval():
    root = Path(__file__).resolve().parents[1]
    result = audit_submission(root, '0.10')
    assert result['regulatory_evidence']['status'] == 'REQUIRES_REVIEW'
    assert result['regulatory_evidence']['expert_signoff'] == 'NOT_VERIFIED'
    assert result['submission_ready'] is False

def test_pending_reviews_are_counted(tmp_path):
    (tmp_path / 'kb').mkdir()
    (tmp_path / 'kb/sources.json').write_text(json.dumps([
        {'id':'s1','legal_review':'pending'}, {'id':'s2','legal_review':'verified'}]))
    (tmp_path / 'kb/claims.json').write_text(json.dumps([
        {'id':'c1','review':'pending'}, {'id':'c2','review':'verified'}]))
    result = audit_submission(tmp_path, '0.10')
    assert result['regulatory_evidence']['sources_not_verified'] == 1
    assert result['regulatory_evidence']['claims_not_verified'] == 1
    assert result['submission_ready'] is False

def test_missing_evidence_does_not_count_as_verified(tmp_path):
    result = audit_submission(tmp_path, '0.10')
    assert result['regulatory_evidence']['sources_not_verified'] is None
    assert result['regulatory_evidence']['status'] == 'REQUIRES_REVIEW'
