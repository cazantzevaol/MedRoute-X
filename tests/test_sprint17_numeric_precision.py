"""MILP float conversion must never silently round synthetic pack counts."""
from copy import deepcopy
import pytest
from medroute.scenarios import flagship
from medroute.optimizer import optimize, validate_operational, MAX_EXACT_INTEGER


@pytest.mark.parametrize('field, value', [
    ('stock', MAX_EXACT_INTEGER + 1),
    ('daily_demand', MAX_EXACT_INTEGER + 1),
    ('reserve_days', MAX_EXACT_INTEGER + 1),
    ('priority', MAX_EXACT_INTEGER + 1),
])
def test_unsafe_site_integer_rejected(field, value):
    case = flagship()
    case['sites'][0][field] = value
    with pytest.raises(ValueError, match='exactly representable'):
        optimize(case, 'greedy')
    with pytest.raises(ValueError):
        validate_operational(case, {'transfers': []})


def test_multiplication_overflow_rejected():
    case = flagship()
    case['sites'][0]['daily_demand'] = MAX_EXACT_INTEGER // 2
    with pytest.raises(ValueError, match='exceeds exact integer range'):
        optimize(case, 'optimized')


def test_ordinary_synthetic_scenario_remains_valid():
    case = deepcopy(flagship())
    assert validate_operational(case, optimize(case, 'optimized'))['passes']
