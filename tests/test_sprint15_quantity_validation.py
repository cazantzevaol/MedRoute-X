"""Safety regression: synthetic inventory and route values cannot be rounded silently."""
from copy import deepcopy
import pytest
from medroute.scenarios import flagship
from medroute.optimizer import optimize, validate_operational
from medroute.engine import Sandbox


@pytest.mark.parametrize('field,value', [
    ('stock', 12.9), ('daily_demand', True), ('reserve_days', -1),
    ('priority', 0), ('stock', float('nan')),
])
def test_invalid_site_quantities_fail_closed(field, value):
    case = flagship()
    case['sites'][0][field] = value
    with pytest.raises(ValueError):
        optimize(case)


@pytest.mark.parametrize('field,value', [
    ('capacity', 1.9), ('capacity', -1), ('days', 1.5),
    ('temperature_ok', 1),
])
def test_invalid_route_quantities_fail_closed(field, value):
    case = flagship()
    case['routes'][0][field] = value
    with pytest.raises(ValueError):
        optimize(case)


def test_independent_validator_also_rejects_fractional_route_capacity():
    case = flagship()
    plan = optimize(case)
    case['routes'][0]['capacity'] = 20.5
    with pytest.raises(ValueError):
        validate_operational(case, plan)


def test_sandbox_rejects_invalid_synthetic_input():
    case = deepcopy(flagship())
    case['sites'][0]['stock'] = 7.5
    with pytest.raises(ValueError):
        Sandbox(case)


def test_integer_scenario_remains_usable():
    state = Sandbox(flagship()).state()
    assert state['simulation_only'] is True
    assert state['legal_check']['status'] == 'HUMAN_REVIEW_REQUIRED'
