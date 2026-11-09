"""Reject ambiguous synthetic graph identities before computing proposals."""
import pytest
from medroute.optimizer import optimize, validate_operational
from medroute.scenarios import flagship
from medroute.engine import Sandbox


@pytest.mark.parametrize('mutation', [
    lambda c: c['sites'][1].update(id=c['sites'][0]['id']),
    lambda c: c['sites'][0].update(id=''),
    lambda c: c['routes'][1].update(id=c['routes'][0]['id']),
    lambda c: c['routes'][0].update(id=''),
    lambda c: c['routes'][0].update(to='Unknown site'),
    lambda c: c['routes'][0].update(to=c['routes'][0]['from']),
])
def test_invalid_graph_fails_closed_in_optimizer_and_validator(mutation):
    case = flagship()
    mutation(case)
    with pytest.raises(ValueError):
        optimize(case, method='greedy')
    with pytest.raises(ValueError):
        validate_operational(case, {'transfers': []})
    with pytest.raises(ValueError):
        Sandbox(case)


def test_valid_graph_still_produces_simulation_only_plan():
    case = flagship()
    assert optimize(case, method='greedy')['baseline_unmet'] >= 0
    assert validate_operational(case, {'transfers': []})['passes']
