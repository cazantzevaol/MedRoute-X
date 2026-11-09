"""Reject non-finite solver output rather than treating it as a feasible proposal."""
import copy
from unittest.mock import patch
import pytest
from scipy.optimize import OptimizeResult
from medroute.optimizer import optimize

SCENARIO = {
    'horizon_days': 2,
    'sites': [
        {'id': 'A', 'stock': 20, 'daily_demand': 1, 'reserve_days': 1, 'priority': 1},
        {'id': 'B', 'stock': 0, 'daily_demand': 5, 'reserve_days': 1, 'priority': 2},
    ],
    'routes': [{'id': 'R', 'from': 'A', 'to': 'B', 'capacity': 10, 'days': 1, 'temperature_ok': True}],
}

@pytest.mark.parametrize('bad', [None, [float('nan')], [float('inf')], [float('-inf')], []])
@pytest.mark.parametrize('stage', [1, 2])
def test_rejects_invalid_solver_output(bad, stage):
    valid = OptimizeResult(success=True, x=[10.0], message='ok')
    invalid = OptimizeResult(success=True, x=bad, message='ok')
    outputs = [invalid] if stage == 1 else [valid, invalid]
    with patch('scipy.optimize.milp', side_effect=outputs):
        with pytest.raises(RuntimeError, match='missing or non-finite'):
            optimize(copy.deepcopy(SCENARIO))
