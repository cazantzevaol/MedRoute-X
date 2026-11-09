"""No live global example may masquerade as UAE legal authority."""
from medroute.llm import validate_agent_result

SOURCE = 'Global policy example requires coordination between authorities.'
SCOPE = {'G1': 'CONTEXT_ONLY_NOT_UAE_LEGAL_BASIS'}


def result(summary, scope=SCOPE):
    return validate_agent_result({'summary': summary, 'cited_claim_ids': ['G1'],
                                  'evidence_quotes': {'G1': SOURCE}},
                                 {'G1'}, {'G1': SOURCE}, require_quotes=True,
                                 evidence_scope=scope)


def test_foreign_example_without_label_is_withheld():
    r = result('This regulation establishes authorization for UAE shipment.')
    assert r['citation_integrity'] == 'FOREIGN_SCOPE_UNLABELLED'
    assert 'foreign_evidence_scope_unlabelled' in r['safety_flags']
    assert 'withheld' in r['summary']
    assert r['evidence_quotes_anchored'] == {}
    assert r['autonomous_transfer_authorized'] is False


def test_explicit_global_comparison_remains_review_only():
    r = result('Global comparative example, not UAE law; seek local review.')
    assert r['citation_integrity'] == 'IDS_ALLOWLISTED'
    assert r['foreign_context_reference_count'] == 1
    assert r['evidence_entailment_verified'] is False
    assert r['legal_status'] == 'HUMAN_REVIEW_REQUIRED'


def test_uae_scoped_evidence_not_falsely_blocked():
    r = result('UAE procedure requires review.', {'G1': 'UNVERIFIED_UAE_APPLICABILITY'})
    assert r['citation_integrity'] == 'IDS_ALLOWLISTED'
    assert r['foreign_context_reference_count'] == 0


def test_legacy_no_scope_preserved():
    r = result('Review required.', {})
    assert r['citation_integrity'] == 'IDS_ALLOWLISTED'
