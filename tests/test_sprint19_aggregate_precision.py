"""Prevent aggregate route-capacity precision loss in float64 MILP."""
from copy import deepcopy
import pytest
from medroute.optimizer import MAX_EXACT_INTEGER, optimize, validate_operational
from medroute.scenarios import flagship

@pytest.mark.parametrize('method', ['optimized', 'greedy', 'local_only'])
def test_aggregate_capacity_overflow_fails_closed(method):
    case = deepcopy(flagship())
    case['routes'][0]['capacity'] = MAX_EXACT_INTEGER
    case['routes'][1]['capacity'] = 1
    with pytest.raises(ValueError, match='aggregate route capacity'):
        optimize(case, method=method)


def test_independent_validator_rejects_aggregate_overflow():
    case = flagship()
    case['routes'][0]['capacity'] = MAX_EXACT_INTEGER
    case['routes'][1]['capacity'] = 1
    with pytest.raises(ValueError, match='aggregate route capacity'):
        validate_operational(case, {'transfers': []})


def test_capacity_at_exact_integer_limit_is_allowed():
    case = flagship()
    for route in case['routes']:
        route['capacity'] = 0
    case['routes'][0]['capacity'] = MAX_EXACT_INTEGER
    result = optimize(case, method='greedy')
    assert validate_operational(case, result)['passes']
