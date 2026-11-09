"""Regression tests for 2026 EDE supply-chain policy context (synthetic only)."""
from medroute.knowledge import catalog, claims, search_claims, permission_verdict, validate_evidence_integrity

SOURCE = 'EDE-SUPPLY-RESILIENCE-2026'
CLAIM = 'C-EDE-SUPPLY-2026-001'


def test_2026_policy_has_traceable_official_provenance():
    source = next(s for s in catalog() if s['id'] == SOURCE)
    claim = next(c for c in claims() if c['id'] == CLAIM)
    assert source['url'].startswith('https://www.ede.gov.ae/')
    assert claim['source_id'] == source['id']
    assert 'pending' in source['legal_review']
    assert 'pending' in claim['review']
    assert validate_evidence_integrity(catalog(), claims())['integrity'] == 'PASS'


def test_new_2026_context_is_retrievable_but_not_legal_clearance():
    hits = search_claims('multiple authorised agents supply resilience', limit=20)
    matching = [h for h in hits if h['id'] == CLAIM]
    assert len(matching) == 1
    assert matching[0]['legal_clearance'] is False
    assert matching[0]['human_legal_review_required'] is True
    assert matching[0]['legal_applicability'] == 'UNVERIFIED_UAE_APPLICABILITY'


def test_supply_policy_never_authorizes_a_synthetic_transfer():
    verdict = permission_verdict([{'medicine': 'SYNTHETIC-DRUG', 'quantity': 1}])
    assert verdict['status'] == 'HUMAN_REVIEW_REQUIRED'
    assert 'approved' not in verdict['message'].lower().replace('not approved', '')


def test_policy_is_not_an_emergency_controlled_medicine_permit():
    verdict = permission_verdict([{'medicine': 'SYNTHETIC-DRUG', 'quantity': 1}],
                                 product_category='controlled_or_psychotropic', emergency_declared=True)
    assert verdict['status'] == 'HUMAN_REVIEW_REQUIRED'
    assert verdict['regulatory_pathway'] is not None
