"""Synthetic adversarial evidence-free narratives; no external model calls."""
from medroute.llm import validate_agent_result


def test_live_permission_claim_without_citation_is_withheld():
    r = validate_agent_result({'summary': 'Regulation permits transfer',
                               'open_questions': ['Proceed with dispatch?']},
                              {'C1'}, {'C1': 'Review is required.'}, require_quotes=True)
    assert r['citation_integrity'] == 'NO_EVIDENCE'
    assert r['safety_flags'] == ['missing_live_evidence']
    assert 'withheld' in r['summary']
    assert r['open_questions'] == []
    assert r['autonomous_transfer_authorized'] is False


def test_legacy_offline_no_citations_preserved():
    r = validate_agent_result({'summary': 'No evidence found'}, {'C1'})
    assert r['summary'] == 'No evidence found'
    assert r['safety_flags'] == []


def test_live_valid_quoted_reference_not_blocked_by_missing_evidence():
    source = 'A human must review the proposed transfer.'
    r = validate_agent_result({'summary': 'Review required',
                               'cited_claim_ids': ['C1'],
                               'evidence_quotes': {'C1': source}},
                              {'C1'}, {'C1': source}, require_quotes=True)
    assert r['citation_integrity'] == 'IDS_ALLOWLISTED'
    assert r['summary'] == 'Review required'
    assert r['evidence_entailment_verified'] is False
