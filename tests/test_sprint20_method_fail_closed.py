"""Unknown optimizer methods must never silently yield a no-transfer plan."""
import pytest
from medroute.optimizer import optimize


@pytest.mark.parametrize('routes', [[], [{'id': 'r', 'from': 'a', 'to': 'b', 'capacity': 1, 'days': 1, 'temperature_ok': True}]])
@pytest.mark.parametrize('method', ['optimised', 'local-only', '', None])
def test_unknown_method_rejected_even_when_no_routes(routes, method):
    scenario = {'horizon_days': 1, 'sites': [
        {'id': 'a', 'stock': 3, 'daily_demand': 0, 'reserve_days': 0, 'priority': 1},
        {'id': 'b', 'stock': 0, 'daily_demand': 2, 'reserve_days': 0, 'priority': 1}], 'routes': routes}
    with pytest.raises(ValueError, match='Unknown method'):
        optimize(scenario, method=method)
