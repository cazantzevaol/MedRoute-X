"""Bounded numeric-only import for synthetic facility and route scenarios."""
from .scenarios import flagship


def template():
    sample = flagship()
    ids = {site['id']: i for i, site in enumerate(sample['sites'], 1)}
    return {
        'horizon_days': sample['horizon_days'],
        'sites': [{**site, 'id': ids[site['id']]} for site in sample['sites']],
        'routes': [{**route, 'id': i, 'from': ids[route['from']], 'to': ids[route['to']]}
                   for i, route in enumerate(sample['routes'], 1)],
    }


def _fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{label}: expected fields {", ".join(expected)}.')


def _integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label}: expected an integer from {low} to {high}.')
    return value


def _rows(value, minimum, maximum, label):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f'{label}: expected {minimum} to {maximum} entries.')
    return value


def parse_scenario(data):
    _fields(data, ('horizon_days', 'sites', 'routes'), 'Scenario')
    horizon = _integer(data['horizon_days'], 1, 30, 'horizon_days')
    sites, routes = [], []
    site_ids, route_ids = set(), set()
    for site in _rows(data['sites'], 1, 20, 'sites'):
        _fields(site, ('id', 'stock', 'daily_demand', 'reserve_days', 'priority'), 'Site')
        ident = _integer(site['id'], 1, 999, 'Site id')
        if ident in site_ids:
            raise ValueError('Site ids must be unique.')
        site_ids.add(ident)
        for key, low, high in (('stock', 0, 10000), ('daily_demand', 0, 10000),
                               ('reserve_days', 0, 30), ('priority', 1, 5)):
            _integer(site[key], low, high, f'Site {key}')
        sites.append({**site, 'id': f'Facility {ident}'})

    for route in _rows(data['routes'], 0, 60, 'routes'):
        _fields(route, ('id', 'from', 'to', 'capacity', 'days', 'temperature_ok',
                        'requires_approval'), 'Route')
        ident = _integer(route['id'], 1, 999, 'Route id')
        if ident in route_ids:
            raise ValueError('Route ids must be unique.')
        route_ids.add(ident)
        origin = _integer(route['from'], 1, 999, 'Route from')
        destination = _integer(route['to'], 1, 999, 'Route to')
        if origin == destination or not {origin, destination} <= site_ids:
            raise ValueError('Route endpoints must be different existing site ids.')
        _integer(route['capacity'], 0, 10000, 'Route capacity')
        _integer(route['days'], 0, 30, 'Route days')
        if type(route['temperature_ok']) is not bool or type(route['requires_approval']) is not bool:
            raise ValueError('Route flags must be true or false.')
        routes.append({**route, 'id': f'Route {ident}', 'from': f'Facility {origin}',
                       'to': f'Facility {destination}'})

    return {
        'id': 'CUSTOM', 'title': 'Imported synthetic scenario',
        'product': 'Synthetic essential medicine X', 'product_category': 'unspecified',
        'emergency_declared': False, 'horizon_days': horizon, 'sites': sites,
        'routes': routes, 'events': [], 'notes': 'Local synthetic scenario.',
    }
