"""No network: strict evidence anchoring for live agent narratives."""
from medroute.llm import validate_agent_result

E = {'E-1': 'Human authorization must be reviewed before any shipment.'}


def test_live_unquoted_reference_withheld():
    result = validate_agent_result({'summary': 'Policy permits shipment',
        'cited_claim_ids': ['E-1'], 'open_questions': ['Can we ship?']},
        set(E), E, require_quotes=True)
    assert 'withheld' in result['summary']
    assert result['open_questions'] == []
    assert result['citation_integrity'] == 'INCOMPLETE_QUOTE_COVERAGE'
    assert result['unquoted_reference_count'] == 1
    assert result['autonomous_transfer_authorized'] is False


def test_live_valid_quote_remains_review_only():
    result = validate_agent_result({'summary': 'Human review needed',
        'cited_claim_ids': ['E-1'],
        'evidence_quotes': {'E-1': 'Human authorization must be reviewed'}},
        set(E), E, require_quotes=True)
    assert result['summary'] == 'Human review needed'
    assert result['evidence_entailment_verified'] is False
    assert result['legal_status'] == 'HUMAN_REVIEW_REQUIRED'


def test_live_no_citations_no_quote_violation():
    result = validate_agent_result({'summary': 'No evidence found'},
        set(E), E, require_quotes=True)
    assert result['unquoted_reference_count'] == 0
    assert result['safety_flags'] == ['missing_live_evidence']
    assert result['citation_integrity'] == 'NO_EVIDENCE'
    assert 'withheld' in result['summary']


def test_legacy_compatibility_unquoted_remains_review_only():
    result = validate_agent_result({'summary': 'Review', 'cited_claim_ids': ['E-1']}, set(E), E)
    assert result['summary'] == 'Review'
    assert result['evidence_entailment_verified'] is False
