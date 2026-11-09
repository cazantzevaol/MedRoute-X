"""Synthetic evidence-reference laundering regressions; no API or patient data."""
from medroute.llm import validate_agent_result


def test_forged_citation_explicitly_flagged_without_authorization():
    result = validate_agent_result({'summary': 'Review needed',
                                   'cited_claim_ids': ['C-OK', 'C-FORGED']}, {'C-OK'})
    assert result['cited_claim_ids'] == ['C-OK']
    assert result['citation_integrity'] == 'UNRECOGNIZED_REFERENCES'
    assert result['unrecognized_reference_count'] == 1
    assert result['safety_flag'] == 'unrecognized_evidence_reference'
    assert result['evidence_entailment_verified'] is False
    assert result['autonomous_transfer_authorized'] is False


def test_forged_reference_beyond_display_limit_is_not_silently_ignored():
    refs = ['C-OK'] * 20 + ['C-FORGED']
    result = validate_agent_result({'summary': 'Review', 'cited_claim_ids': refs}, {'C-OK'})
    assert result['unrecognized_reference_count'] == 1
    assert result['citation_integrity'] == 'UNRECOGNIZED_REFERENCES'


def test_non_string_reference_is_flagged():
    result = validate_agent_result({'summary': 'Review', 'cited_claim_ids': [None, 123]}, set())
    assert result['unrecognized_reference_count'] == 2
    assert result['cited_claim_ids'] == []


def test_allowlisted_reference_does_not_claim_semantic_verification():
    result = validate_agent_result({'summary': 'Review', 'cited_claim_ids': ['C-OK']}, {'C-OK'})
    assert result['citation_integrity'] == 'IDS_ALLOWLISTED'
    assert result['safety_flag'] == 'none'
    assert result['evidence_entailment_verified'] is False


def test_unsafe_approval_flag_has_priority_over_forged_citation():
    result = validate_agent_result({'summary': 'I authorize transfer now',
                                   'cited_claim_ids': ['FAKE']}, set())
    assert result['safety_flag'] == 'unsafe_approval_language_redacted'
    assert result['unrecognized_reference_count'] == 1
