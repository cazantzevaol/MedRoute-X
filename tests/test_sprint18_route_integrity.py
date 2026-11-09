"""Synthetic-only fail-closed validation of impossible delivery and overflow."""
from copy import deepcopy
import pytest
from medroute.scenarios import flagship
from medroute.optimizer import optimize, validate_operational, MAX_EXACT_INTEGER

@pytest.mark.parametrize('method', ['greedy', 'optimized', 'local_only'])
def test_zero_day_route_rejected_by_all_methods(method):
    case = deepcopy(flagship())
    case['routes'][0]['days'] = 0
    with pytest.raises(ValueError, match='route.days must be positive'):
        optimize(case, method=method)

def test_zero_day_route_rejected_by_independent_validator():
    case = deepcopy(flagship())
    case['routes'][0]['days'] = 0
    with pytest.raises(ValueError, match='route.days must be positive'):
        validate_operational(case, {'transfers': []})

def test_excessive_plan_quantity_rejected():
    case = flagship()
    plan = {'transfers': [{'route': 'B-A', 'from': 'Hospital B', 'to': 'Hospital A',
                           'quantity': MAX_EXACT_INTEGER + 1}]}
    result = validate_operational(case, plan)
    assert not result['passes']
    assert any('Invalid nonnegative integer quantity' in issue for issue in result['issues'])

def test_normal_synthetic_case_still_works():
    case = flagship()
    plan = optimize(case, method='greedy')
    assert validate_operational(case, plan)['passes']
