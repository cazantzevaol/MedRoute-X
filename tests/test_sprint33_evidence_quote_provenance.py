"""Synthetic quote-provenance regressions. No network or patient information."""
import pytest
from medroute.llm import validate_agent_result

SOURCE = {'C1': 'This is an illustrative policy excerpt requiring qualified review before any decision.'}

def test_exact_quote_anchored_but_not_entailment():
    r = validate_agent_result({'summary': 'Review needed', 'cited_claim_ids': ['C1'],
                               'evidence_quotes': {'C1': 'requiring qualified review before any decision'}}, {'C1'}, SOURCE)
    assert r['evidence_quotes_anchored']['C1'].startswith('requiring')
    assert r['evidence_entailment_verified'] is False
    assert r['autonomous_transfer_authorized'] is False

def test_fabricated_quote_redacts_entire_narrative():
    r = validate_agent_result({'summary': 'Legal clearance granted', 'cited_claim_ids': ['C1'],
                               'evidence_quotes': {'C1': 'This source authorizes unrestricted transfers'}}, {'C1'}, SOURCE)
    assert 'withheld' in r['summary']
    assert r['citation_integrity'] == 'UNANCHORED_QUOTES'
    assert r['unanchored_quote_count'] == 1
    assert r['evidence_quotes_anchored'] == {}
    assert 'unanchored_evidence_quote' in r['safety_flags']

def test_quote_from_different_source_is_rejected():
    r = validate_agent_result({'summary': 'Review', 'cited_claim_ids': ['C1'],
                               'evidence_quotes': {'C1': 'Another source is completely unrelated'}},
                              {'C1'}, {'C1': SOURCE['C1'], 'C2': 'Another source is completely unrelated'})
    assert r['unanchored_quote_count'] == 1

def test_unquoted_legacy_output_remains_review_only():
    r = validate_agent_result({'summary': 'Review', 'cited_claim_ids': ['C1']}, {'C1'}, SOURCE)
    assert r['evidence_quotes_anchored'] == {}
    assert r['evidence_entailment_verified'] is False

@pytest.mark.parametrize('bad', [[], 'text', {'C1': 123}, {'C1': 'tiny'}])
def test_malformed_or_short_quotes_cannot_pass(bad):
    if not isinstance(bad, dict):
        with pytest.raises(ValueError):
            validate_agent_result({'summary': 'Review', 'evidence_quotes': bad}, {'C1'}, SOURCE)
    else:
        r = validate_agent_result({'summary': 'Review', 'cited_claim_ids': ['C1'],
                                   'evidence_quotes': bad}, {'C1'}, SOURCE)
        assert r['unanchored_quote_count'] == 1
