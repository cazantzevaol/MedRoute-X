"""Local-dashboard HTTP boundary tests. No network outside loopback is used."""
import json
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

import medroute.server as server_module
from medroute.engine import Sandbox


@contextmanager
def running_server(monkeypatch):
    monkeypatch.setattr(server_module, 'GAME', Sandbox())
    server = ThreadingHTTPServer(('127.0.0.1', 0), server_module.Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', server.server_port
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def call(base, path, method='GET', headers=None, data=None):
    request = Request(base + path, data=data, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except HTTPError as error:
        return error.code, error.headers, error.read()


def post(base, **kwargs):
    headers = {'Content-Type': 'application/json', 'X-MedRoute-Request': 'dashboard-v1'}
    headers.update(kwargs.pop('headers', {}))
    return call(base, '/api/step', 'POST', headers, kwargs.pop('data', b'{}'))


def test_valid_dashboard_get_and_post_remain_functional(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, headers, payload = call(base, '/api/state')
        assert status == 200
        assert json.loads(payload)['step'] == 0
        check_scenario_import(base)
        assert headers['X-Content-Type-Options'] == 'nosniff'
        assert headers['X-Frame-Options'] == 'DENY'
        status, _, payload = post(base, headers={'Origin': base, 'Sec-Fetch-Site': 'same-origin'})
        assert status == 200
        assert json.loads(payload)['step'] == 1
        assert call(base, '/api/state')[0] == 200


@pytest.mark.parametrize('path', ['/', '/app.js', '/api/state', '/api/dossier', '/api/council'])
def test_dns_rebinding_host_is_rejected_for_every_get(monkeypatch, path):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = call(base, path, headers={'Host': f'attacker.example:{port}'})
        assert status == 421


def test_dns_rebinding_host_cannot_change_scenario(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = post(base, headers={'Host': f'attacker.example:{port}'})
        assert status == 421
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_cross_origin_post_cannot_change_scenario(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = post(base, headers={'Origin': 'https://attacker.example'})
        assert status == 403
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_cross_site_fetch_metadata_is_rejected(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = post(base, headers={'Sec-Fetch-Site': 'cross-site'})
        assert status == 403
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_missing_custom_header_blocks_form_post(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = call(base, '/api/step', 'POST',
                            {'Content-Type': 'application/x-www-form-urlencoded'}, b'{}')
        assert status == 403
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_invalid_json_post_does_not_change_state(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = post(base, data=b'not-json')
        assert status == 400
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_wrong_content_type_post_does_not_change_state(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = post(base, headers={'Content-Type': 'text/plain'})
        assert status == 415
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_read_endpoint_does_not_advance(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        assert call(base, '/api/step')[0] == 404
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_localhost_alias_accepted_for_same_port(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, payload = call(base, '/api/state', headers={'Host': f'localhost:{port}'})
        assert status == 200
        assert json.loads(payload)['step'] == 0


def test_host_with_wrong_port_is_rejected(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = call(base, '/api/state', headers={'Host': f'localhost:{port+1}'})
        assert status == 421


def test_null_origin_cannot_write(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, _, _ = post(base, headers={'Origin': 'null'})
        assert status == 403
        assert json.loads(call(base, '/api/state')[2])['step'] == 0


def test_reset_still_works_with_dashboard_headers(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        assert post(base)[0] == 200
        assert json.loads(call(base, '/api/state')[2])['step'] == 1
        status, _, payload = call(base, '/api/reset', 'POST',
                                  {'Content-Type': 'application/json',
                                   'X-MedRoute-Request': 'dashboard-v1'}, b'{}')
        assert status == 200
        assert json.loads(payload)['step'] == 0


def test_preflight_does_not_enable_cross_origin_access(monkeypatch):
    with running_server(monkeypatch) as (base, port):
        status, headers, _ = call(base, '/api/step', 'OPTIONS',
                                  {'Origin': 'https://attacker.example',
                                   'Access-Control-Request-Method': 'POST'})
        assert status == 405
        assert 'Access-Control-Allow-Origin' not in headers

@pytest.mark.parametrize('framing', [
    b'Content-Length: 3\r\n',
    b'Content-Length: 2\r\nContent-Length: 2\r\n',
    b'Content-Length: 2\r\nTransfer-Encoding: chunked\r\n',
    b'Content-Length: +2\r\n',
])
def test_ambiguous_or_incomplete_post_cannot_advance(monkeypatch, framing):
    import socket

    with running_server(monkeypatch) as (base, port):
        with socket.create_connection(('127.0.0.1', port), timeout=5) as client:
            client.sendall(
                f'POST /api/step HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'.encode()
                + b'Content-Type: application/json\r\n'
                + b'X-MedRoute-Request: dashboard-v1\r\n'
                + framing + b'\r\n{}'
            )
            client.shutdown(socket.SHUT_WR)
            with client.makefile('rb') as response:
                assert response.readline().split()[1] == b'400'
        assert json.loads(call(base, '/api/state')[2])['step'] == 0
        with monkeypatch.context() as patch:
            def fail_calculation(scenario):
                raise RuntimeError('private diagnostic')

            patch.setattr('medroute.engine.optimize', fail_calculation)
            status, _, body = post(base)
            assert status == 500
            assert json.loads(body) == {'error': 'Simulation update failed'}
            assert json.loads(call(base, '/api/state')[2])['step'] == 0
        assert post(base)[0] == 200


def check_scenario_import(base):
    headers = {'Content-Type': 'application/json', 'X-MedRoute-Request': 'dashboard-v1'}
    status, response_headers, body = call(base, '/api/scenario/template')
    assert status == 200
    assert response_headers['Content-Disposition'] == 'attachment; filename="synthetic-scenario.json"'
    data = json.loads(body)
    data['sites'][0]['stock'] = 21
    data['horizon_days'] = 7

    def upload(payload):
        return call(base, '/api/scenario', 'POST', headers, json.dumps(payload).encode())

    status, _, body = upload(data)
    assert status == 200
    imported = json.loads(body)
    assert imported['scenario']['id'] == 'CUSTOM'
    assert imported['scenario']['sites'][0]['stock'] == 21
    assert imported['steps_total'] == 0
    hospital = next(agent for agent in imported['agents'] if agent['agent'] == 'Hospital')
    assert 'over 7 days' in hospital['summary']
    data['routes'][0]['to'] = 999
    assert upload(data)[0] == 400
    data['extra'] = 'private text'
    status, _, body = upload(data)
    assert status == 400 and b'private text' not in body
    assert json.loads(call(base, '/api/state')[2]) == imported
    def action(name, payload):
        return call(base, '/api/scenario/' + name, 'POST', headers, json.dumps(payload).encode())

    assert action('confirm', {'disruption_id': 'stale'})[0] == 400
    assert action('disruption', {'route_id': 'Route 1', 'capacity': True})[0] == 400
    status, _, body = action('disruption', {'route_id': 'Route 1', 'capacity': 0})
    assert status == 200
    pending = json.loads(body)
    assert pending['disruption_pending']
    assert pending['scenario']['routes_known'][0]['capacity'] == 70
    assert pending['release_status'] == 'BLOCKED_OPERATIONAL'
    assert action('disruption', {'route_id': 'Route 2', 'capacity': 0})[0] == 400
    assert action('confirm', {'disruption_id': 'stale'})[0] == 400
    assert json.loads(call(base, '/api/state')[2]) == pending
    status, _, body = action('confirm', {'disruption_id': pending['disruption_id']})
    assert status == 200
    confirmed = json.loads(body)
    assert not confirmed['disruption_pending']
    assert confirmed['scenario']['routes_known'][0]['capacity'] == 0
    assert confirmed['operational_check']['passes']
    assert any(entry['kind'] == 'DEMO_OPERATOR_CONFIRMATION' for entry in confirmed['audit'])
    assert action('confirm', {'disruption_id': 'stale'})[0] == 400
    status, _, body = call(base, '/api/reset', 'POST', headers, b'{}')
    assert status == 200
    reset = json.loads(body)
    assert reset['step'] == 0 and reset['steps_total'] == 0
    assert reset['scenario']['routes_known'][0]['capacity'] == 70
    status, _, body = call(base, '/api/agents/run', 'POST', headers,
                           json.dumps({'roles': ['Supplier', 'Coordinator', 'Auditor']}).encode())
    assert status == 200
    result = json.loads(body)
    assert [item['role'] for item in result['trace']] == ['Supplier', 'Coordinator', 'Auditor']
    assert all(item['transfer_authorized'] is False for item in result['trace'])
    for invalid in ([], ['Supplier', 'Supplier'], ['Unknown'], [True]):
        assert call(base, '/api/agents/run', 'POST', headers,
                    json.dumps({'roles': invalid}).encode())[0] == 400
    # Larger facility networks follow the same import, calculation and export contract.
    expanded = json.loads(call(base, '/api/scenario/template')[2])
    for ident in range(4, 21):
        expanded['sites'].append({'id': ident, 'stock': 0, 'daily_demand': 3,
                                  'reserve_days': 1, 'priority': 1})
    expanded['routes'].append({'id': 4, 'from': 2, 'to': 4, 'capacity': 5,
                               'days': 1, 'temperature_ok': True, 'requires_approval': True})
    status, _, body = upload(json.loads(json.dumps(expanded)))
    assert status == 200
    larger = json.loads(body)
    assert len(larger['scenario']['sites']) == 20
    assert len(larger['plan']['unmet_by_site']) == 20
    assert larger['plan']['baseline_unmet'] == 72 + 17 * 15
    assert larger['operational_check']['passes']
    assert larger['legal_check']['status'] == 'HUMAN_REVIEW_REQUIRED'
    assert any(r['to'] == 'Facility 4' for r in larger['scenario']['routes_known'])
    expanded['sites'].append({'id':21,'stock':0,'daily_demand':3,'reserve_days':1,'priority':1})
    assert upload(expanded)[0] == 400
    assert json.loads(call(base, '/api/state')[2]) == larger
    status, _, body = call(base, '/api/scenario/example', 'POST', headers, b'{}')
    assert status == 200
    assert json.loads(body)['scenario']['id'] == 'CASE-001'
