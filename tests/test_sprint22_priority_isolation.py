"""Stage-two institutional priority cannot be overridden by travel-day scale."""
from medroute.optimizer import optimize, validate_operational


def scenario(high_days, low_days):
    return {'horizon_days': 5000, 'sites': [
        {'id': 'donor', 'stock': 1, 'daily_demand': 0, 'reserve_days': 0, 'priority': 1},
        {'id': 'high', 'stock': 0, 'daily_demand': 1, 'reserve_days': 0, 'priority': 2},
        {'id': 'low', 'stock': 0, 'daily_demand': 1, 'reserve_days': 0, 'priority': 1}],
        'routes': [
            {'id': 'to_high', 'from': 'donor', 'to': 'high', 'capacity': 1,
             'days': high_days, 'temperature_ok': True},
            {'id': 'to_low', 'from': 'donor', 'to': 'low', 'capacity': 1,
             'days': low_days, 'temperature_ok': True}]}


def test_long_on_time_high_priority_route_wins():
    s = scenario(5000, 1)
    result = optimize(s)
    assert result['transfers'] == [{'route': 'to_high', 'from': 'donor', 'to': 'high', 'quantity': 1}]
    assert validate_operational(s, result)['passes']


def test_priority_not_affected_by_reversing_travel_days():
    s = scenario(1, 5000)
    assert optimize(s)['transfers'][0]['route'] == 'to_high'
