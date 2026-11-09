"""Reject solver output that violates discrete operational constraints."""
from types import SimpleNamespace
import pytest
import scipy.optimize
from medroute.optimizer import optimize


def scenario():
    return {'horizon_days': 2, 'sites': [
        {'id': 'a', 'stock': 5, 'daily_demand': 0, 'reserve_days': 0, 'priority': 1},
        {'id': 'b', 'stock': 0, 'daily_demand': 5, 'reserve_days': 0, 'priority': 1}],
        'routes': [{'id': 'r', 'from': 'a', 'to': 'b', 'capacity': 5,
                    'days': 1, 'temperature_ok': True}]}


@pytest.mark.parametrize('stage2_value', [6.0, 4.0, 4.25])
def test_reject_solver_invalid_second_stage(monkeypatch, stage2_value):
    calls = iter([SimpleNamespace(success=True, x=[5.0]),
                  SimpleNamespace(success=True, x=[stage2_value])])
    monkeypatch.setattr(scipy.optimize, 'milp', lambda **kwargs: next(calls))
    with pytest.raises(RuntimeError, match='MILP solution failed|non-integral'):
        optimize(scenario())


def test_reject_nonintegral_first_stage(monkeypatch):
    monkeypatch.setattr(scipy.optimize, 'milp', lambda **kwargs:
                        SimpleNamespace(success=True, x=[4.25]))
    with pytest.raises(RuntimeError, match='Stage-one MILP returned non-integral'):
        optimize(scenario())


def test_valid_solver_solution_still_accepted():
    result = optimize(scenario())
    assert result['transfers'][0]['quantity'] == 5
