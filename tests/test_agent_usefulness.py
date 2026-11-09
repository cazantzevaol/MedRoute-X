"""Useful deterministic assessments without leaking private supplier facts."""
from copy import deepcopy
import pytest
from medroute.agents import observe
from medroute.council import OfflineProvider, run_council
from medroute.engine import Sandbox
from medroute.scenarios import flagship


def assessment(role, scenario):
    view = observe(scenario, role, [], 0)
    view['horizon_days'] = scenario['horizon_days']
    return OfflineProvider().assess(role, view, [], [])['summary']


def test_hospital_and_inventory_use_actual_horizon_and_reserves():
    case = flagship()
    assert '72 synthetic packs' in assessment('Hospital', case)
    assert '90 packs available' in assessment('Inventory', case)
    case['horizon_days'] = 10
    assert '197 synthetic packs' in assessment('Hospital', case)
    assert '30 packs available' in assessment('Inventory', case)


@pytest.mark.parametrize('role', ['Hospital', 'Demand', 'Inventory', 'Equity'])
def test_site_roles_change_with_visible_stock(role):
    case = flagship()
    before = assessment(role, case)
    case['sites'][0]['stock'] = 200
    assert assessment(role, case) != before


def test_missing_horizon_is_explicit_not_assumed():
    view = observe(flagship(), 'Hospital', [], 0)
    assert 'horizon unavailable' in OfflineProvider().assess('Hospital', view, [], [])['summary']


def test_logistics_flags_temperature_and_time_independently():
    case = flagship()
    case['routes'][0]['temperature_ok'] = False
    case['routes'][1]['days'] = 6
    summary = assessment('Logistics', case)
    assert 'Temperature constraint failures: 1' in summary
    assert 'outside the 5-day horizon: 1' in summary


def test_private_supplier_capacity_does_not_leak_and_disclosure_changes_logistics():
    game = Sandbox()
    game.advance()
    before = deepcopy(game.state())
    result = run_council(game)
    rows = {r['role']: r for r in result['trace']}
    assert game.state() == before
    assert 'B-A: 70 packs' in rows['Logistics']['summary']
    assert 'B-A: 15 packs' not in rows['Logistics']['summary']
    assert '15' not in rows['Supplier']['summary']
    assert 'B-A' not in rows['Supplier']['summary']
    assert '1 request formal supplier disclosure' in rows['Coordinator']['summary']
    assert 'NOT PASSED' in rows['Auditor']['summary']
    assert all(not r['transfer_authorized'] for r in result['trace'])
    game.advance()
    rows = {r['role']: r for r in run_council(game)['trace']}
    assert 'B-A: 15 packs' in rows['Logistics']['summary']
    assert '0 request formal supplier disclosure' in rows['Coordinator']['summary']
    assert 'check: PASS' in rows['Auditor']['summary']


def test_supplier_raw_private_text_never_exported_in_summary():
    visible = {'routes': [{'id': 'SECRET-ROUTE', 'capacity': 987654}],
               'received_reports': [{'message': 'SECRET-PAYLOAD'}]}
    result = OfflineProvider().assess('Supplier', visible, [], [])
    assert all(secret not in str(result) for secret in ('SECRET-ROUTE', '987654', 'SECRET-PAYLOAD'))
