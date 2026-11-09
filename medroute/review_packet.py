"""Review packet for a synthetic supply incident."""
from .optimizer import optimize, validate_operational
from .learning import context_key, preferences
from .disclosure import pending_private_supplier_reports


def review_packet(game):
    state = game.state()
    alternatives = []
    for method, title in (('local_only', 'Keep current stocks'),
                          ('greedy', 'Simple redistribution'),
                          ('optimized', 'Priority-aware redistribution')):
        plan = state['plan'] if method == 'optimized' else optimize(game.known, method)
        check = validate_operational(game.world, plan)
        alternatives.append({
            'method': method, 'title': title, 'unmet_packs': plan['unmet_total'],
            'unmet_by_site': plan['unmet_by_site'],
            'weighted_unmet': plan['priority_weighted_unmet'],
            'transfers': plan['transfers'], 'operational_pass': check['passes'],
            'issues': check['issues'], 'transfer_authorized': False,
        })
    valid = [option for option in alternatives if option['operational_pass']]
    context = context_key(game.known, alternatives)
    learned = preferences(context)
    recommendation = min(valid, key=lambda option: (
        option['weighted_unmet'], option['unmet_packs'], -learned.get(option['method'], 0)))
    pending = bool(pending_private_supplier_reports(game.reports))
    tasks = []
    if pending:
        tasks.append({'owner': 'Supplier / Coordinator', 'action': 'Confirm and share the pending route update.',
                      'reason': 'The coordinator may be planning with outdated route facts.'})
    if not state['operational_check']['passes']:
        tasks.append({'owner': 'Logistics', 'action': 'Resolve operational blockers before reviewing the plan.',
                      'reason': ' '.join(state['operational_check']['issues'])})
    if recommendation['unmet_packs']:
        tasks.append({'owner': 'Supply coordinator', 'action': 'Request additional supply availability.',
                      'reason': f"{recommendation['unmet_packs']} packs remain unmet in the operationally valid proposal."})
    if recommendation['transfers']:
        tasks.append({'owner': 'Qualified pharmacy / regulatory reviewer',
                      'action': 'Review product status, facility credentials and transfer permissions.',
                      'reason': state['legal_check']['message']})
    if not tasks:
        tasks.append({'owner': 'Supply coordinator', 'action': 'Review inventory and demand assumptions.',
                      'reason': 'The current scenario has no proposed movement requiring approval.'})
    return {
        'scenario': state['scenario']['title'], 'step': state['step'],
        'learning_context': context, 'learned_preferences': learned,
        'audit_head': state['audit_verification']['head'],
        'data_basis': 'Synthetic coordinator-visible inventory, demand and route facts.',
        'validation_basis': 'Independent checker uses actual synthetic test conditions.',
        'alternatives': alternatives, 'next_action': tasks[0], 'review_tasks': tasks,
        'recommendation': {
            'title': recommendation['title'],
            'method': recommendation['method'],
            'transfers': recommendation['transfers'],
            'unmet_by_site': recommendation['unmet_by_site'],
            'additional_supply_requests': [
                {'facility': site, 'packs': count, 'status': 'AVAILABILITY_UNCONFIRMED'}
                for site, count in recommendation['unmet_by_site'].items() if count > 0],
            'reason': 'Lowest weighted shortfall among valid proposals. Local feedback breaks ties between equally effective options.',
            'provisional': pending,
            'review_note': ('Confirm the pending supplier update and compare plans again.'
                            if pending else 'Review product, facility and transfer permissions before action.'),
            'transfer_authorized': False,
        },
        'policy_questions': state['policy_matrix']['rows'],
        'evidence': state['evidence'], 'human_authorization_required': True,
        'status': 'DRAFT_FOR_HUMAN_REVIEW',
    }
