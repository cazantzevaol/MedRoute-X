"""Seeded experiment: honest comparisons on synthetic medicine continuity cases."""
import json
from statistics import mean
from .scenarios import benchmark_scenarios
from .optimizer import optimize, validate_operational
from .engine import Sandbox


def evaluate(count=30, seed=2026):
    if not 1 <= count <= 500:
        raise ValueError('count must be between 1 and 500')
    cases = benchmark_scenarios(count=count, seed=seed)
    records = []
    for case in cases:
        game = Sandbox(case)
        game.advance(); game.advance()  # coordinator learns verified supplier update
        for method in ('local_only', 'greedy', 'optimized'):
            proposal = optimize(game.known, method=method)
            check = validate_operational(game.world, proposal)
            records.append({'scenario': case['id'], 'method': method,
                            'unmet_units': proposal['unmet_total'],
                            'priority_weighted_unmet': proposal['priority_weighted_unmet'],
                            'improvement_units': proposal['baseline_unmet']-proposal['unmet_total'],
                            'operational_valid': check['passes'],
                            'legal_approval': 'not_granted_by_demo'})
    stats = {}
    for method in ('local_only', 'greedy', 'optimized'):
        group = [r for r in records if r['method'] == method]
        stats[method] = {'scenarios': len(group),
                         'mean_unmet_units': round(mean(x['unmet_units'] for x in group), 2),
                         'mean_improvement_units': round(mean(x['improvement_units'] for x in group), 2),
                         'mean_priority_weighted_unmet': round(mean(x['priority_weighted_unmet'] for x in group), 2),
                         'operational_valid_rate': round(mean(x['operational_valid'] for x in group), 3)}
    baseline = stats['greedy']['mean_priority_weighted_unmet']
    improvement = round((baseline - stats['optimized']['mean_priority_weighted_unmet']) / baseline * 100, 2) if baseline else 0
    return {'description': 'Synthetic inventory and urgency weights only. These are NOT clinical, law, or real inventory results.',
            'method_notes': {'local_only': 'no inter-facility coordination',
                             'greedy': 'simple capacity-constrained transfers in route order',
                             'optimized': 'two-stage integer program: units then institutional urgency weights'},
            'priority_weighted_reduction_vs_greedy_percent': improvement,
            'seed': seed, 'stats': stats, 'records': records}

if __name__ == '__main__':
    print(json.dumps(evaluate(), indent=2, ensure_ascii=False))
