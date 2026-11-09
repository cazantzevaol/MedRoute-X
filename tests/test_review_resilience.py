"""Failures in optional local helpers cannot manufacture success or permission."""
import io
import json
import sqlite3

import pytest

from medroute import learning
from medroute.engine import Sandbox
from medroute.local_ai import BriefingUnavailable, local_briefing
from medroute.review_packet import review_packet


def test_corrupt_preferences_preserve_review_and_disclosure(monkeypatch, tmp_path):
    database = tmp_path / 'corrupt.sqlite3'
    database.write_bytes(b'not a database')
    monkeypatch.setattr(learning, 'DB_PATH', database)
    game = Sandbox()
    game.advance()
    assert game.state()['pending_supplier_disclosure'] is True
    packet = review_packet(game)
    chosen = next(x for x in packet['alternatives'] if x['method'] == packet['recommendation']['method'])
    assert chosen['operational_pass']
    assert sum(x['packs'] for x in packet['recommendation']['additional_supply_requests']) == chosen['unmet_packs']
    assert packet['learned_preferences'] == {}
    game.advance()
    assert game.state()['pending_supplier_disclosure'] is False


@pytest.mark.parametrize('envelope', [None, [], {}, {'response': '[]', 'done': True},
                                    {'response': '{"focus":[]}', 'done': True}])
def test_malformed_local_ai_is_explicitly_unavailable(monkeypatch, envelope):
    monkeypatch.setenv('MEDROUTE_LOCAL_MODEL', 'test-local')
    transport = lambda *args, **kwargs: io.BytesIO(json.dumps(envelope).encode())
    with pytest.raises(BriefingUnavailable):
        local_briefing(Sandbox().state(), transport=transport)


def test_feedback_write_failure_returns_service_error(monkeypatch):
    from test_sprint3_http_boundary import running_server, call
    from medroute import server
    def fail(*args):
        raise sqlite3.OperationalError('disk failure')
    monkeypatch.setattr(server, 'save_preference', fail)
    with running_server(monkeypatch) as (base, _):
        packet = json.loads(call(base, '/api/review-packet')[2])
        payload = json.dumps({'audit_head': packet['audit_head'],
                              'method': packet['recommendation']['method'], 'useful': True}).encode()
        status, _, response = call(base, '/api/review-feedback', 'POST',
                                  {'Content-Type': 'application/json', 'X-MedRoute-Request': 'dashboard-v1'}, payload)
        assert status == 503
        assert 'not saved' in json.loads(response)['error']
        assert call(base, '/api/state')[0] == 200
