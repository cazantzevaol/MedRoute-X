"""No legal approval may be inferred from source summaries or claim matching."""
from medroute.knowledge import evidence_assurance, search_claims
from medroute.council import _evidence_for_role
from medroute.regulatory import transfer_pathway


def test_search_exposes_legal_assurance_and_review_metadata():
    hits = search_claims('UAE emergency transfer medicine approval', limit=20)
    assert hits
    assert all(h['legal_clearance'] is False for h in hits)
    assert all(h['human_legal_review_required'] is True for h in hits)
    assert all(h['source_review_status'] for h in hits)
    assert all(h['claim_review_status'] for h in hits)


def test_uae_evidence_is_not_a_transfer_permit():
    hits = search_claims('EDE emergency narcotic psychotropic transfer', jurisdiction='UAE')
    assert hits
    assert all(h['legal_applicability'] == 'UNVERIFIED_UAE_APPLICABILITY' for h in hits)
    assert all(h['legal_clearance'] is False for h in hits)


def test_foreign_comparator_never_becomes_uae_legal_basis():
    hits = search_claims('EMA EU solidarity shortage')
    assert any(h['jurisdiction'].startswith('EU') for h in hits)
    for hit in hits:
        if hit['jurisdiction'].startswith('EU'):
            assert hit['legal_applicability'] == 'CONTEXT_ONLY_NOT_UAE_LEGAL_BASIS'
            assert hit['legal_clearance'] is False


def test_spoofed_approved_metadata_cannot_grant_clearance():
    claim = {'review': 'approved', 'jurisdiction': 'UAE'}
    source = {'legal_review': 'approved', 'jurisdiction': 'UAE'}
    result = evidence_assurance(claim, source)
    assert result['legal_clearance'] is False
    assert result['human_legal_review_required'] is True
    assert result['legal_applicability'] == 'UNVERIFIED_UAE_APPLICABILITY'


def test_mismatched_jurisdiction_fails_closed():
    claim = {'review': 'verified', 'jurisdiction': 'UAE'}
    source = {'legal_review': 'verified', 'jurisdiction': 'EU/EEA'}
    result = evidence_assurance(claim, source)
    assert result['legal_applicability'] == 'CONTEXT_ONLY_NOT_UAE_LEGAL_BASIS'
    assert result['legal_clearance'] is False


def test_council_evidence_carries_human_review_boundary():
    evidence = _evidence_for_role('Regulator', 'controlled_or_psychotropic', True)
    assert evidence
    assert all(row['legal_clearance'] is False for row in evidence)
    assert all(row['human_legal_review_required'] for row in evidence)
    assert all('legal_applicability' in row for row in evidence)
    assert transfer_pathway([{'synthetic': True}], 'controlled_or_psychotropic', True)['authorization_granted'] is False


def test_full_council_passes_assurance_metadata_to_provider():
    from medroute.council import run_council
    from medroute.engine import Sandbox

    class RecordingProvider:
        mode = 'offline_recording_test'

        def __init__(self):
            self.seen = []

        def assess(self, role, visible, evidence, handoffs):
            self.seen.append((role, evidence))
            assert all(e['legal_clearance'] is False for e in evidence)
            assert all(e['human_legal_review_required'] is True for e in evidence)
            return {'summary': 'Qualified human review is required.',
                    'cited_claim_ids': [], 'open_questions': []}

    provider = RecordingProvider()
    result = run_council(Sandbox(), provider=provider)
    assert len(provider.seen) == 10
    assert all(not row['transfer_authorized'] for row in result['trace'])
    assert result['human_approval_required'] is True
