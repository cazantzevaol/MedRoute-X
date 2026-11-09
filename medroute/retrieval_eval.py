"""Small, explicit, reproducible retrieval checks for *source summaries*.

This is not a validation of current laws, legal entailment, or generalization.
"""
import json
from pathlib import Path
from .knowledge import search_claims, claims

GOLD_FILE = Path(__file__).resolve().parent.parent / 'benchmarks/policy_retrieval_gold.json'


def evaluate_retrieval(gold_file=GOLD_FILE, k=3):
    path = Path(gold_file)
    if not path.is_absolute() and not path.is_file():
        path = Path(__file__).resolve().parent.parent / path
    tests = json.loads(path.read_text(encoding='utf-8'))['cases']
    existing = {c['id'] for c in claims()}
    if not tests or len({t['id'] for t in tests}) != len(tests):
        raise ValueError('Gold cases must be nonempty and have unique IDs')
    for item in tests:
        if item['gold_claim_id'] not in existing:
            raise ValueError(f'Unknown expected claim: {item["gold_claim_id"]}')
    results = []
    for case in tests:
        ranked = [r['id'] for r in search_claims(case['query'], limit=k)]
        rank = ranked.index(case['gold_claim_id']) + 1 if case['gold_claim_id'] in ranked else None
        results.append({'id': case['id'], 'gold_claim_id': case['gold_claim_id'],
                        'top_ids': ranked, 'gold_rank': rank, 'hit_at_1': rank == 1,
                        'hit_at_k': rank is not None})
    return {'scope': 'curated high-level source summaries only', 'n': len(tests), 'k': k,
            'hit_at_1': round(sum(r['hit_at_1'] for r in results)/len(results), 3),
            'hit_at_k': round(sum(r['hit_at_k'] for r in results)/len(results), 3),
            'mrr_at_k': round(sum(1/r['gold_rank'] if r['gold_rank'] else 0 for r in results)/len(results), 3),
            'cases': results, 'limitation': 'Not a national corpus benchmark, no semantic legal entailment assessment.'}

if __name__ == '__main__':
    print(json.dumps(evaluate_retrieval(), indent=2, ensure_ascii=False))
