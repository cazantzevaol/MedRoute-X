"""Inspectable role prototypes with asymmetric observations.

Not LLM agents yet. Every role gets a constrained view and generates a bounded,
checkable recommendation. The auditor and policy officer never grant permissions.
"""
from .optimizer import compute_needs
from .knowledge import search_claims, permission_verdict, gap_hypothesis

ROLES = ['Coordinator', 'Hospital', 'Inventory', 'Demand', 'Supplier', 'Logistics',
         'Regulator', 'GlobalPolicy', 'Equity', 'Auditor']

ROLE_MANDATES = {
    'Coordinator': 'Integrate reports and request approvals; cannot initiate transfers',
    'Hospital': 'Report facility shortage and care continuity needs (no patient records)',
    'Inventory': 'Validate stock, reserves and consistency of inventory quantities',
    'Demand': 'Estimate unmet modeled demand over the planning horizon',
    'Supplier': 'Receive supplier capacity updates and identify alternative supply options',
    'Logistics': 'Assess transport capacity, timing and temperature constraints',
    'Regulator': 'Raise legal-authorization questions; may not issue legal permissions',
    'GlobalPolicy': 'Provide international comparisons labeled by jurisdiction',
    'Equity': 'Compare unmet demand across institutions using synthetic weights',
    'Auditor': 'Independently inspect evidence and operational validation; never self-authorize',
}


def observe(scenario, role, reports, step):
    if role not in ROLES:
        raise ValueError(f'Unknown role: {role}')
    view = {'role': role, 'step': step, 'scenario_id': scenario['id'],
            'mandate': ROLE_MANDATES[role]}
    if role in ('Hospital', 'Inventory', 'Demand', 'Equity', 'Coordinator', 'Auditor'):
        view['sites'] = [dict(s) for s in scenario['sites']]
    if role in ('Supplier', 'Logistics', 'Coordinator', 'Auditor'):
        view['routes'] = [dict(r) for r in scenario['routes']]
    if role in ('Regulator', 'GlobalPolicy', 'Auditor'):
        view['source_refs'] = [r['id'] for r in search_claims('medicine policy law EU UAE')]
    if role in ('Regulator', 'Coordinator', 'Auditor'):
        view['product_category'] = scenario.get('product_category', 'unspecified')
        view['emergency_declared'] = scenario.get('emergency_declared', False)
    view['received_reports'] = [dict(r) for r in reports if role in r['visible_to']]
    for report in view['received_reports']:
        change = report.get('change')
        if change and 'routes' in view:
            for route in view['routes']:
                if route['id'] == change['route_id']:
                    route['capacity'] = change['capacity']
    return view


def findings(scenario, plan, reports, step, product_category='unspecified', emergency_declared=False):
    needs, spare = compute_needs(scenario)
    perm, gap = permission_verdict(plan['transfers'], product_category, emergency_declared), gap_hypothesis()
    messages = []
    for role in ROLES:
        view = observe(scenario, role, reports, step)
        if role == 'Coordinator':
            summary = ('Proposal awaits independent operational validation and human authorization; '
                       'only disclosures addressed to Coordinator change its route facts.')
            refs = ['C-ITU-002']
        elif role == 'Hospital':
            horizon = scenario['horizon_days']
            summary = f'Modeled shortage over {horizon} days totals {sum(needs.values())} synthetic packs.'
            refs = ['C-WHO-001']
        elif role == 'Inventory':
            summary = 'Donor spare after safety reserves: ' + ', '.join(f'{k}={v}' for k,v in spare.items())
            refs = []
        elif role == 'Demand':
            summary = f'Proposed plan leaves {plan["unmet_total"]} generic packs unmet in this model.'
            refs = []
        elif role == 'Supplier':
            received = view['received_reports']
            summary = ('Private supplier report received; other institutions may have stale data.'
                       if received else 'No private supplier update received yet.')
            refs = ['C-EDE-001']
        elif role == 'Logistics':
            summary = f'{len(plan["transfers"])} routes proposed; temperature and capacity checks are separate.'
            refs = []
        elif role == 'Regulator':
            summary = perm['status'] + ': ' + perm['message']
            refs = perm['evidence']
        elif role == 'GlobalPolicy':
            summary = 'EMA EU/EEA solidarity example is non-binding in the UAE.'
            refs = ['C-EMA-001']
        elif role == 'Equity':
            summary = 'Unmet modeled demand by facility: ' + ', '.join(
                f'{site}: {packs} packs' for site, packs in plan['unmet_by_site'].items())
            refs = []
        else:
            summary = 'Audit requires independent validation, evidence traceability, and explicit human clearance.'
            refs = ['C-ITU-002']
        messages.append({'agent': role, 'mandate': ROLE_MANDATES[role],
                         'summary': summary, 'references': refs,
                         'observation_keys': sorted(k for k in view
                                                    if k not in ('role','step','scenario_id','mandate')),
                         'messages_seen': len(view['received_reports'])})
    return {'messages': messages, 'legal_gate': perm, 'gap_hypothesis': gap}
