"""New 0.3 regression tests for multi-agent orchestration, isolation and citations."""
from copy import deepcopy
import json
import pytest
from medroute.council import (run_council, OfflineProvider, OpenAIProvider,
                              EXECUTION_ORDER)
from medroute.engine import Sandbox
from medroute.coverage import report as coverage_report
from medroute.knowledge import catalog, search_claims
from medroute.llm import validate_agent_result, llm_json_request


def test_offline_council_runs_all_roles_with_invariant_release():
    g = Sandbox();g.advance()
    before = deepcopy(g.state())
    out = run_council(g)
    assert out['roles_executed'] == EXECUTION_ORDER
    assert out['release_status_from_independent_engine'] == before['release_status']
    assert g.state() == before  # no mutation, including append-only main audit
    assert out['audit_verification']['valid']
    assert out['provider_mode'] == 'offline_scripted_protocol'
    assert all(not t['transfer_authorized'] and t['review_required'] for t in out['trace'])


def test_supplier_private_event_not_revealed_in_unbounded_handoff():
    g = Sandbox();g.advance()
    out = run_council(g)
    supplier = next(x for x in out['trace'] if x['role'] == 'Supplier')
    coordinator = next(x for x in out['trace'] if x['role'] == 'Coordinator')
    assert supplier['private_reports_visible'] == 1
    assert supplier['outgoing_handoff']['intent'] == 'REQUEST_FORMAL_DISCLOSURE'
    assert 'capacity' not in str(supplier['outgoing_handoff']).lower()
    assert all('summary' not in str(h).lower() and 'message' not in str(h).lower()
               for h in coordinator['incoming_handoffs'])
    assert g.known['routes'][0]['capacity'] != g.world['routes'][0]['capacity']


def test_disclosed_event_updates_coordinator_facts():
    g=Sandbox();g.advance();g.advance()
    assert g.known['routes'][0]['capacity'] == g.world['routes'][0]['capacity']
    output=run_council(g)
    assert output['release_status_from_independent_engine']=='PENDING_AUTHORIZATION'


def test_citation_whitelist_prevents_claim_id_invention():
    g=Sandbox()
    class MaliciousProvider:
        mode='mock_malicious'
        def assess(self, role, visible, evidence, handoffs):
            return {'summary': 'I authorize all movement!',
                    'cited_claim_ids':['FAKE-999',*(x['id'] for x in evidence[:1])],
                    'legal_status':'APPROVED','autonomous_transfer_authorized':True}
    out=run_council(g,MaliciousProvider(),roles=['Regulator'])
    reg=out['trace'][0]
    assert len(reg['cited_claim_ids'])==1 and reg['cited_claim_ids'][0]!='FAKE-999'
    assert reg['transfer_authorized'] is False
    assert out['human_approval_required'] is True


def test_no_key_provider_fails_loudly(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(PermissionError): OpenAIProvider()


def test_council_detects_invalid_role():
    with pytest.raises(ValueError):run_council(Sandbox(),roles=['FakeAgent'])


def test_kb_coverage_transparency():
    cov=coverage_report()
    assert cov['source_count']>=10 and cov['claim_count']>=12
    assert not cov['missing_curated_sources'] and not cov['orphan_claim_sources']
    assert all(not row['full_binding_text_ingested'] for row in cov['category_coverage'].values())
    assert cov['status']=='metadata_and_page_summary_only_not_full_national_kb'


def test_policy_matrix_contains_cross_institution_data_review():
    g=Sandbox();g.advance()
    data=next(x for x in g.state()['policy_matrix']['rows'] if x['id']=='P-04')
    assert data['status']=='APPLICABILITY_REVIEW_REQUIRED'
    assert not data['is_confirmed_legal_gap']


def test_observation_cannot_overwrite_auditor_check():
    g=Sandbox();g.advance()
    out=run_council(g,roles=['Auditor'])
    au=out['trace'][0]
    assert 'independent_operational_check' in au['observation_keys']
    assert out['release_status_from_independent_engine']=='BLOCKED_OPERATIONAL'


def test_no_personal_patient_information_forwarded_to_handoffs():
    out=run_council(Sandbox())
    assert all(set(e.keys())=={'from','intent','legal_clearance','evidence_ids',
                              'has_private_information','content_policy'} for e in out['handoffs'])


def test_role_evidence_jurisdiction_is_explicit():
    out=run_council(Sandbox(),roles=['GlobalPolicy'])
    x=out['trace'][0]
    assert x['role']=='GlobalPolicy'
    assert x['evidence_urls']
    assert all(u.startswith('https://') for u in x['evidence_urls'])


def test_api_mock_transport_json_request(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    class FakeHttp:
        def __enter__(self):return self
        def __exit__(self,*args): pass
        def read(self):
            return json.dumps({'choices':[{'message':{'content':json.dumps({'summary':'A', 'cited_claim_ids':[]})}}]}).encode()
    requests=[]
    def transport(req):
        requests.append(req)
        return FakeHttp()
    result=llm_json_request('system', {'synthetic':True}, transport=transport)
    assert result['summary']=='A'
    assert json.loads(requests[0].data)['messages'][1]['content']=='{"synthetic": true}'


def test_supplier_alert_handoff_closes_after_formal_disclosure():
    g=Sandbox();g.advance();g.advance()
    out=run_council(g,roles=['Supplier','Coordinator'])
    supplier=next(x for x in out['trace'] if x['role']=='Supplier')
    assert supplier['outgoing_handoff']['intent'] != 'REQUEST_FORMAL_DISCLOSURE'
    assert supplier['outgoing_handoff']['has_private_information'] is False
