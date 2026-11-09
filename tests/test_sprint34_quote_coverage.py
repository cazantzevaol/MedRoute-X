"""Synthetic partial-evidence laundering regressions; no external API."""
from medroute.llm import validate_agent_result

E = {'A': 'Alpha regulation requires independent human confirmation.',
     'B': 'Beta guidance does not grant automatic transfer authorization.'}

def test_partial_quote_coverage_fails_closed():
    result = validate_agent_result({'summary': 'Both regulations permit transport',
        'cited_claim_ids': ['A', 'B'],
        'evidence_quotes': {'A': 'requires independent human confirmation'}}, set(E), E)
    assert 'withheld' in result['summary']
    assert result['citation_integrity'] == 'INCOMPLETE_QUOTE_COVERAGE'
    assert 'incomplete_evidence_quote_coverage' in result['safety_flags']
    assert result['unquoted_reference_count'] == 1
    assert result['evidence_quotes_anchored'] == {}
    assert result['autonomous_transfer_authorized'] is False

def test_complete_quotes_stay_anchored_without_claiming_entailment():
    result = validate_agent_result({'summary': 'Human review required',
        'cited_claim_ids': ['A', 'B'],
        'evidence_quotes': {'A': 'requires independent human confirmation',
                            'B': 'does not grant automatic transfer authorization'}}, set(E), E)
    assert result['citation_integrity'] == 'IDS_ALLOWLISTED'
    assert result['unquoted_reference_count'] == 0
    assert len(result['evidence_quotes_anchored']) == 2
    assert result['evidence_entailment_verified'] is False

def test_legacy_unquoted_is_explicitly_unverified():
    result = validate_agent_result({'summary': 'Review required',
        'cited_claim_ids': ['A']}, set(E), E)
    assert result['unquoted_reference_count'] == 1
    assert result['evidence_entailment_verified'] is False
