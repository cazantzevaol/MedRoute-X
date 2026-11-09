"""Regression tests for private-report non-disclosure and event-scoped acknowledgements."""
from copy import deepcopy
import json

from medroute.council import run_council, verify_council_artifact
from medroute.engine import Sandbox
from medroute.policy import evidence_dossier
from medroute.scenarios import flagship


def _multi_alert_scenario():
    scenario = deepcopy(flagship())
    scenario['events'] = [
        {'title': 'Private B-A reduction', 'change': {'route_id': 'B-A', 'capacity': 15},
         'visible_to': ['Supplier'], 'message': 'private-A-8401'},
        {'title': 'B-A disclosed', 'reveal': ['B-A'],
         'visible_to': ['Coordinator', 'Auditor'], 'message': 'B-A disclosed for review'},
        {'title': 'Private B-C reduction', 'change': {'route_id': 'B-C', 'capacity': 8},
         'visible_to': ['Supplier'], 'message': 'private-C-8402'},
        {'title': 'B-C disclosed', 'reveal': ['B-C'],
         'visible_to': ['Coordinator', 'Auditor'], 'message': 'B-C disclosed for review'},
    ]
    return scenario


def _supplier_alert(game):
    council = run_council(game, roles=['Supplier', 'Coordinator', 'Auditor'])
    assert verify_council_artifact(council)['valid']
    supplier = next(row for row in council['trace'] if row['role'] == 'Supplier')
    return supplier['outgoing_handoff'], council


def test_private_event_payload_is_not_in_public_state_or_evidence_export():
    scenario = deepcopy(flagship())
    scenario['events'][0]['message'] = 'supplier-private-marker-8421'
    scenario['events'][0]['change']['capacity'] = 13
    game = Sandbox(scenario)
    game.advance()
    assert 'supplier-private-marker-8421' in str(game.reports)
    state = game.state()
    assert 'supplier-private-marker-8421' not in json.dumps(state)
    assert 'supplier-private-marker-8421' not in json.dumps(evidence_dossier(state))
    assert all('change' not in row for row in state['reports'])
    assert state['reports'][0]['visibility'] == 'RESTRICTED'


def test_new_private_alert_after_old_disclosure_requires_new_handoff():
    game = Sandbox(_multi_alert_scenario())
    game.advance()
    first, _ = _supplier_alert(game)
    assert first['intent'] == 'REQUEST_FORMAL_DISCLOSURE'
    game.advance()
    cleared, _ = _supplier_alert(game)
    assert cleared['intent'] != 'REQUEST_FORMAL_DISCLOSURE'
    game.advance()
    second, council = _supplier_alert(game)
    assert second['intent'] == 'REQUEST_FORMAL_DISCLOSURE'
    assert second['has_private_information'] is True
    assert 'private-C-8402' not in json.dumps(council)
    assert next(row for row in game.state()['policy_matrix']['rows'] if row['id'] == 'P-02')['status'] == 'REVIEW_REQUIRED'
    game.advance()
    resolved, _ = _supplier_alert(game)
    assert resolved['intent'] != 'REQUEST_FORMAL_DISCLOSURE'
    assert next(row for row in game.state()['policy_matrix']['rows'] if row['id'] == 'P-02')['status'] == 'DISCLOSED_FOR_REVIEW'


def test_unrelated_formal_disclosure_cannot_clear_supplier_alert():
    scenario = deepcopy(flagship())
    scenario['events'][1]['reveal'] = ['B-C']  # unrelated to private B-A update
    game = Sandbox(scenario)
    game.advance()
    game.advance()
    alert, _ = _supplier_alert(game)
    assert alert['intent'] == 'REQUEST_FORMAL_DISCLOSURE'
    assert next(row for row in game.state()['policy_matrix']['rows'] if row['id'] == 'P-02')['status'] == 'REVIEW_REQUIRED'


def test_public_api_endpoints_do_not_expose_private_report(monkeypatch):
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.request import urlopen
    import medroute.server as server_module

    scenario = deepcopy(flagship())
    scenario['events'][0]['message'] = 'private-api-marker-9907'
    game = Sandbox(scenario)
    game.advance()
    monkeypatch.setattr(server_module, 'GAME', game)
    server = ThreadingHTTPServer(('127.0.0.1', 0), server_module.Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        for endpoint in ('/api/state', '/api/dossier', '/api/council'):
            with urlopen(f'http://127.0.0.1:{server.server_port}{endpoint}', timeout=10) as response:
                payload = response.read().decode('utf-8')
            assert 'private-api-marker-9907' not in payload
            assert json.loads(payload)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=10)


def test_public_request_digest_cannot_be_used_as_capacity_oracle():
    """A public hash of a small integer would allow enumeration of capacities."""
    scenario1 = deepcopy(flagship())
    scenario2 = deepcopy(flagship())
    scenario1['events'][0]['change']['capacity'] = 11
    scenario2['events'][0]['change']['capacity'] = 12
    first = Sandbox(scenario1)
    second = Sandbox(scenario2)
    first.advance()
    second.advance()
    a = run_council(first, roles=['Supplier'])['trace'][0]
    b = run_council(second, roles=['Supplier'])['trace'][0]
    assert a['public_request_sha256'] == b['public_request_sha256']
    assert 'request_sha256' not in a  # raw, potentially guessable data is not hashed publicly


def test_new_uae_law_pointer_is_metadata_only_not_legal_clearance():
    from medroute.knowledge import catalog, claims
    from medroute.coverage import report
    src = next(s for s in catalog() if s['id'] == 'UAE-FDL38-2024')
    claim = next(c for c in claims() if c['source_id'] == src['id'])
    assert src['url'].startswith('https://uaelegislation.gov.ae/')
    assert src['legal_review'].startswith('pending')
    assert 'not_product_specific_authorization' in claim['effect']
    assert not report()['category_coverage']['medical_product_law']['full_binding_text_ingested']


def test_reusable_second_scenario_reopens_after_new_private_alert():
    from medroute.scenarios import multi_alert_disclosure
    game = Sandbox(multi_alert_disclosure())
    statuses = []
    for step in range(5):
        if step:
            game.advance()
        handoff, _ = _supplier_alert(game)
        statuses.append(handoff['intent'])
    assert [x == 'REQUEST_FORMAL_DISCLOSURE' for x in statuses] == [False, True, False, True, False]
