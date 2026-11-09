"""Red-team tests: evidence must not be silently truncated before verification."""
from medroute.llm import validate_agent_result


def test_eight_valid_refs_fail_closed_even_when_first_seven_quoted():
    ids = [f'C{i}' for i in range(8)]
    source = {i: f'Official excerpt for {i} requiring human review.' for i in ids}
    raw = {'summary': 'All sources support this interpretation',
           'cited_claim_ids': ids,
           'evidence_quotes': {i: source[i] for i in ids[:7]}}
    result = validate_agent_result(raw, set(ids), source, require_quotes=True)
    assert result['citation_integrity'] == 'REFERENCE_OVERFLOW'
    assert 'evidence_reference_overflow' in result['safety_flags']
    assert 'withheld' in result['summary']
    assert result['evidence_quotes_anchored'] == {}
    assert result['reference_overflow_count'] == 1


def test_more_than_twenty_repeated_refs_fail_closed():
    source = {'C1': 'Human review is required for every proposed transfer.'}
    result = validate_agent_result({'summary': 'Transfer is compliant',
                                    'cited_claim_ids': ['C1'] * 21,
                                    'evidence_quotes': {'C1': source['C1']}},
                                   {'C1'}, source, require_quotes=True)
    assert result['citation_integrity'] == 'REFERENCE_OVERFLOW'
    assert result['reference_overflow_count'] == 1
    assert 'withheld' in result['summary']


def test_seven_distinct_valid_refs_with_quotes_remain_visible():
    ids = [f'C{i}' for i in range(7)]
    source = {i: f'Official excerpt for {i} requiring human review.' for i in ids}
    result = validate_agent_result({'summary': 'Evidence for review only',
                                    'cited_claim_ids': ids,
                                    'evidence_quotes': source}, set(ids), source,
                                   require_quotes=True)
    assert result['citation_integrity'] == 'IDS_ALLOWLISTED'
    assert result['summary'] == 'Evidence for review only'
    assert result['reference_overflow_count'] == 0
