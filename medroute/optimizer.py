"""Deterministic integer optimization of *proposals* (never actual drug movements).

Synthetic stock quantities are generic packs, not patient doses.  The model enforces
operational constraints; legal clearance is separate and never implied by this solver.
"""
from collections import defaultdict

# SciPy MILP uses IEEE-754 doubles; larger integers cannot be represented exactly.
MAX_EXACT_INTEGER = (1 << 53) - 1


def validate_scenario_quantities(scenario):
    """Fail closed on invalid synthetic pack counts and route constraints.

    Fractional quantities must never be silently truncated into a plausible plan.
    This validates simulation arithmetic, not legal authorization.
    """
    def integer(value, label, *, positive=False):
        if type(value) is not int or value < (1 if positive else 0) or value > MAX_EXACT_INTEGER:
            raise ValueError(f'{label} must be a {"positive" if positive else "nonnegative"} exactly representable integer (<= {MAX_EXACT_INTEGER})')

    integer(scenario['horizon_days'], 'horizon_days', positive=True)
    # Identifiers are primary keys in the optimizer and independent validator.
    # Duplicate IDs otherwise collapse dictionary entries or route capacities.
    site_ids = set()
    for site in scenario['sites']:
        sid = site['id']
        if not isinstance(sid, str) or not sid.strip() or sid in site_ids:
            raise ValueError('Site IDs must be unique nonempty strings')
        site_ids.add(sid)
    route_ids = set()
    for route in scenario['routes']:
        rid = route['id']
        if not isinstance(rid, str) or not rid.strip() or rid in route_ids:
            raise ValueError('Route IDs must be unique nonempty strings')
        route_ids.add(rid)
        if (route['from'] not in site_ids or route['to'] not in site_ids
                or route['from'] == route['to']):
            raise ValueError(f'Route {rid} must connect distinct known sites')
    for site in scenario['sites']:
        for key in ('stock', 'daily_demand', 'reserve_days'):
            integer(site[key], f'site.{key}')
        integer(site['priority'], 'site.priority', positive=True)
        if site['priority'] > 1000:
            raise ValueError('site.priority must be <= 1000 to keep optimization weights bounded')
        # Multiplication feeds both the LP constraints and the unmet-demand score.
        if scenario['horizon_days'] * site['daily_demand'] > MAX_EXACT_INTEGER:
            raise ValueError('horizon_days * site.daily_demand exceeds exact integer range')
        if max(scenario['horizon_days'], site['reserve_days']) * site['daily_demand'] > MAX_EXACT_INTEGER:
            raise ValueError('reserve/demand product exceeds exact integer range')
    # Stage-one MILP maximizes the SUM of route quantities using float64.
    # Each capacity being exact is insufficient if their aggregate is not.
    # Reject ambiguous totals rather than silently rounding the optimum.
    if sum(route['capacity'] for route in scenario['routes']) > MAX_EXACT_INTEGER:
        raise ValueError('aggregate route capacity exceeds exact integer range')
    for route in scenario['routes']:
        for key in ('capacity', 'days'):
            integer(route[key], f'route.{key}')
        if route['days'] == 0:
            raise ValueError('route.days must be positive: zero-day delivery is not modeled')
        if type(route['temperature_ok']) is not bool:
            raise ValueError('route.temperature_ok must be boolean')


def compute_needs(scenario):
    validate_scenario_quantities(scenario)
    h = scenario['horizon_days']
    needs, spare = {}, {}
    for site in scenario['sites']:
        if any(site[k] < 0 for k in ('stock', 'daily_demand', 'reserve_days')):
            raise ValueError('Negative stock/demand/reserve is not allowed')
        needs[site['id']] = max(0, int(h * site['daily_demand'] - site['stock']))
        spare[site['id']] = max(0, int(site['stock'] - max(site['reserve_days'], h) * site['daily_demand']))
    return needs, spare


def eligible_routes(scenario):
    h = scenario['horizon_days']
    return [r for r in scenario['routes'] if r['capacity'] > 0
            and r['temperature_ok'] and r['days'] <= h]


def _solve_milp(**problem):
    from scipy.optimize import milp
    from warnings import catch_warnings, filterwarnings

    # HiGHS has its own thread pool. Keep local HTTP workers from creating
    # native solver pools as successive requests move between worker threads.
    with catch_warnings():
        filterwarnings('ignore', message=r"Unrecognized options detected: .*threads",
                       category=RuntimeWarning)
        return milp(**problem, options={'time_limit': 10, 'threads': 1})


def _integer_program(scenario, routes):
    """Two-stage lexicographic MILP: maximize units, then prioritize facility urgency.

    Unlike continuous LP followed by rounding, integer MILP cannot round a proposal
    into a route capacity, donor reserve or receiver need violation.
    """
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint

    needs, spare = compute_needs(scenario)
    ids = {s['id']: s for s in scenario['sites']}
    if not routes:
        return []
    constraints = []
    for donor, capacity in spare.items():
        constraints.append(([int(r['from'] == donor) for r in routes], capacity))
    for recipient, capacity in needs.items():
        constraints.append(([int(r['to'] == recipient) for r in routes], capacity))
    A = np.array([row for row, _ in constraints], dtype=float)
    b = np.array([lim for _, lim in constraints], dtype=float)
    bounds = Bounds(np.zeros(len(routes)), np.array([r['capacity'] for r in routes]))
    integrality = np.ones(len(routes), dtype=int)
    limits = LinearConstraint(A, -np.inf, b)
    stage1 = _solve_milp(c=-np.ones(len(routes)), integrality=integrality,
                         bounds=bounds, constraints=limits)
    if not stage1.success:
        raise RuntimeError(f'Integer optimization failed: {stage1.message}')
    if stage1.x is None or len(stage1.x) != len(routes) or not np.all(np.isfinite(stage1.x)):
        raise RuntimeError('Stage-one MILP returned missing or non-finite quantities')
    if any(abs(float(x) - round(float(x))) > 1e-6 for x in stage1.x):
        raise RuntimeError('Stage-one MILP returned non-integral quantities')
    max_units = sum(int(round(float(x))) for x in stage1.x)
    # Stage two enforces the maximum covered units before prioritizing urgency.
    A2 = np.vstack([A, np.ones(len(routes))])
    lo2 = np.array([-np.inf] * len(b) + [max_units], dtype=float)
    hi2 = np.array(list(b) + [max_units], dtype=float)
    # Priorities are illustrative institutional service weights, NOT patient triage.
    # Do not mix delivery days into this objective: a long-but-on-time route
    # could otherwise defeat higher institutional priority. Timeliness is
    # already enforced as an eligibility constraint above.
    cost = np.array([-ids[r['to']]['priority'] for r in routes], dtype=float)
    stage2 = _solve_milp(c=cost, integrality=integrality, bounds=bounds,
                         constraints=LinearConstraint(A2, lo2, hi2))
    if not stage2.success:
        raise RuntimeError(f'Priority optimization failed: {stage2.message}')
    if stage2.x is None or len(stage2.x) != len(routes) or not np.all(np.isfinite(stage2.x)):
        raise RuntimeError('Stage-two MILP returned missing or non-finite quantities')
    if any(abs(float(x) - round(float(x))) > 1e-6 for x in stage2.x):
        raise RuntimeError('Stage-two MILP returned non-integral quantities')
    moves = [{'route': r['id'], 'from': r['from'], 'to': r['to'],
              'quantity': int(round(float(x)))} for r, x in zip(routes, stage2.x) if x >= .5]
    # Solver feasibility tolerances must never be mistaken for operational approval.
    verification = validate_operational(scenario, {'transfers': moves})
    if not verification['passes'] or sum(t['quantity'] for t in moves) != max_units:
        raise RuntimeError('MILP solution failed independent integer validation: '
                           + '; '.join(verification['issues']))
    return moves


def optimize(scenario, method='optimized'):
    """Compute a candidate plan using only the coordinator's currently known facts."""
    if method not in ('local_only', 'greedy', 'optimized'):
        raise ValueError(f'Unknown method: {method}')
    needs, spare = compute_needs(scenario)
    routes = eligible_routes(scenario)
    if method == 'local_only' or not routes:
        moves = []
    elif method == 'greedy':
        moves = []
        for r in sorted(routes, key=lambda x: (x['to'], x['from'], x['id'])):
            q = min(r['capacity'], spare[r['from']], needs[r['to']])
            if q > 0:
                moves.append({'route': r['id'], 'from': r['from'],
                              'to': r['to'], 'quantity': int(q)})
                spare[r['from']] -= q
                needs[r['to']] -= q
    elif method == 'optimized':
        moves = _integer_program(scenario, routes)
    else:
        raise ValueError(f'Unknown method: {method}')
    original_needs, _ = compute_needs(scenario)
    received = defaultdict(int)
    for move in moves:
        received[move['to']] += move['quantity']
    unmet = {site_id: max(0, units - received[site_id]) for site_id, units in original_needs.items()}
    return {'method': method, 'transfers': moves, 'unmet_by_site': unmet,
            'unmet_total': sum(unmet.values()),
            'baseline_unmet': sum(original_needs.values()),
            'priority_weighted_unmet': sum(unmet[s['id']] * s['priority'] for s in scenario['sites'])}


def validate_operational(scenario, plan):
    """Independent validator uses scorer's actual conditions, not an agent's memory."""
    needs, spare = compute_needs(scenario)
    routes = {r['id']: r for r in scenario['routes']}
    sent, received = defaultdict(int), defaultdict(int)
    route_sent, issues = defaultdict(int), []
    for t in plan['transfers']:
        route = routes.get(t.get('route'))
        if not route or route['from'] != t.get('from') or route['to'] != t.get('to'):
            issues.append(f'Invalid route {t.get("route")}')
            continue
        qty = t.get('quantity')
        if type(qty) is not int or qty < 0 or qty > MAX_EXACT_INTEGER:
            issues.append(f'Invalid nonnegative integer quantity on {route["id"]}')
            continue
        route_sent[route['id']] += qty
        if route_sent[route['id']] > route['capacity']:
            issues.append(f'Route capacity exceeded for {route["id"]} (stale information?)')
        if not route['temperature_ok']:
            issues.append(f'Temperature constraint not met for {route["id"]}')
        if route['days'] > scenario['horizon_days']:
            issues.append(f'Delivery too late on {route["id"]}')
        sent[t['from']] += qty
        received[t['to']] += qty
    for origin, qty in sent.items():
        if qty > spare.get(origin, 0):
            issues.append(f'Safety reserve violated at {origin}')
    for dest, qty in received.items():
        if qty > needs.get(dest, 0):
            issues.append(f'Transfers exceed modeled need at {dest}')
    return {'passes': not issues, 'issues': issues}
