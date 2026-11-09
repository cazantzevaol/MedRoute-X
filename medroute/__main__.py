"""python -m medroute [demo|evaluate|sources|audit]"""
import argparse
import json
from .engine import Sandbox
from .scenarios import multi_alert_disclosure, controlled_emergency
from .evaluate import evaluate
from .knowledge import search_claims
from .audit import verify
from .council import run_council
from .coverage import report as coverage_report


def main():
    parser = argparse.ArgumentParser(description='MedRoute X policy-grounded synthetic sandbox')
    parser.add_argument('command', choices=['demo', 'evaluate', 'sources', 'audit', 'council', 'coverage', 'disclosure', 'regulatory'])
    parser.add_argument('--count', type=int, default=30)
    parser.add_argument('--query', default='UAE medicine supply policy')
    args = parser.parse_args()
    if args.command == 'disclosure':
        game = Sandbox(multi_alert_disclosure())
        stages = []
        for step in range(5):
            if step:
                game.advance()
            state = game.state()
            council = run_council(game, roles=['Supplier', 'Coordinator', 'Auditor'])
            supplier = next(x for x in council['trace'] if x['role'] == 'Supplier')
            stages.append({'step': step, 'supplier_handoff_intent':
                           supplier['outgoing_handoff']['intent'],
                           'policy_disclosure_status': next(x['status'] for x in
                           state['policy_matrix']['rows'] if x['id'] == 'P-02'),
                           'operational_check': state['operational_check']['passes'],
                           'release_status': state['release_status'],
                           'public_report_visibility': [r['visibility'] for r in state['reports']]})
        result = {'scenario': 'CASE-002', 'stages': stages,
                  'limitation': 'Synthetic-only; no transfer permission or live LLM.'}
    elif args.command == 'regulatory':
        general = Sandbox().state()
        special = Sandbox(controlled_emergency()).state()
        result = {
            'simulation_only': True,
            'general': {'status': general['release_status'],
                        'pathway': general['legal_check']['regulatory_pathway']},
            'controlled_emergency': {'status': special['release_status'],
                                     'pathway': special['legal_check']['regulatory_pathway'],
                                     'policy_row': next(r for r in special['policy_matrix']['rows']
                                                        if r['id'] == 'P-05')},
            'warning': 'No legal permission; no real products, patients or facility approvals.',
        }
    elif args.command == 'coverage':
        result = coverage_report()
    elif args.command == 'council':
        engine = Sandbox()
        engine.advance()
        result = run_council(engine)
    elif args.command == 'evaluate':
        result = evaluate(count=args.count)
    elif args.command == 'sources':
        result = search_claims(args.query)
    else:
        engine = Sandbox()
        states = [engine.state(), engine.advance(), engine.advance()]
        if args.command == 'audit':
            result = {'validity': verify(engine.audit), 'audit': engine.audit}
        else:
            result = [{'step': s['step'], 'status': s['release_status'],
                       'proposed_transfers': s['plan']['transfers'],
                       'operational_issues': s['operational_check']['issues'],
                       'legal_review': s['legal_check']['status']} for s in states]
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
