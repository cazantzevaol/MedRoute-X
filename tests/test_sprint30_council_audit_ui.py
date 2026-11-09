"""Safety metadata must survive the full council-to-browser export boundary."""
from pathlib import Path
from medroute.council import run_council
from medroute.engine import Sandbox

class ForgedProvider:
    mode = 'offline_mock'
    def assess(self, role, visible, evidence, handoffs):
        return {'summary': 'The policy allows transfer',
                'cited_claim_ids': ['FORGED-ID'] + [e['id'] for e in evidence[:1]]}

def test_forged_evidence_visible_in_council_audit():
    out = run_council(Sandbox(), provider=ForgedProvider(), roles=['Regulator'])
    item = out['trace'][0]
    assert item['citation_integrity'] == 'UNRECOGNIZED_REFERENCES'
    assert item['unrecognized_reference_count'] == 1
    assert item['safety_flags'] == ['unrecognized_evidence_reference']
    assert item['evidence_entailment_verified'] is False
    assert item['legal_status'] == 'HUMAN_REVIEW_REQUIRED'
    assert item['summary'].startswith('Model narrative withheld')
    assert item['transfer_authorized'] is False
    assert out['audit_verification']['valid']

def test_allowlisted_evidence_is_not_claimed_to_be_entailment():
    out = run_council(Sandbox(), roles=['Regulator'])
    item = out['trace'][0]
    assert item['citation_integrity'] == 'IDS_ALLOWLISTED'
    assert item['evidence_entailment_verified'] is False
    assert item['unrecognized_reference_count'] == 0
    assert item['source_details']
    assert all(s['id'] in item['cited_claim_ids'] and s['source_url'].startswith('https://')
               and s['source_title'] and s['legal_clearance'] is False for s in item['source_details'])

def test_browser_exposes_evidence_uncertainty_and_flags():
    js = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text()
    for token in ('a.citation_integrity', 'a.safety_flags',
                  'a.unrecognized_reference_count', 'Entailment NOT verified'):
        assert token in js
