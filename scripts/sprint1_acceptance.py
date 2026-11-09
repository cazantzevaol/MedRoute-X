"""Run reproducible, offline-only sprint-1 acceptance and save a machine artifact."""
import json
from datetime import date
from pathlib import Path
from medroute.engine import Sandbox
from medroute.council import run_council, verify_council_artifact
from medroute.evaluate import evaluate
from medroute.retrieval_eval import evaluate_retrieval
from medroute.knowledge import catalog, claims


def main():
    game = Sandbox()
    steps = []
    for n in range(3):
        if n:
            game.advance()
        state = game.state()
        council = run_council(game)
        steps.append({'step': n, 'release_status': state['release_status'],
                      'independent_operational_pass': state['operational_check']['passes'],
                      'roles': len(council['trace']),
                      'artifact_integrity_verified': verify_council_artifact(council)['valid'],
                      'supplier_handoff_intent': next(h['intent'] for h in council['handoffs'] if h['from']=='Supplier'),
                      'all_movements_pending_human_authorization': all(not t['transfer_authorized'] for t in council['trace'])})
    retrieval = evaluate_retrieval()
    bench = evaluate(count=30, seed=2026)
    summary = {
        'sprint': 'MedRoute X v0.4 sprint 1', 'date': str(date.today()),
        'mode': 'OFFLINE_SCRIPTED_AND_DETERMINISTIC_NO_REAL_LLM_CALLS',
        'knowledge_base': {'source_pointer_count': len(catalog()), 'source_summary_claim_count': len(claims()),
                           'binding_national_texts_included': False},
        'stepwise_scenario': steps,
        'curated_retrieval': {k:v for k,v in retrieval.items() if k!='cases'},
        'synthetic_optimizer': bench['stats'],
        'limit': 'NOT clinical outcome, legal compliance score, national KB performance, or evidence of live model quality.'}
    path = Path('reports/sprint1_acceptance.json')
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'path': str(path), 'steps': steps, 'retrieval': summary['curated_retrieval']}, indent=2))

if __name__=='__main__':
    main()
