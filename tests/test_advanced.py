"""Safety, evidence, integrity and reproducibility regression tests."""
from copy import deepcopy
import pytest
from medroute.engine import Sandbox
from medroute.audit import verify
from medroute.knowledge import claims, search_claims, catalog
from medroute.optimizer import optimize, validate_operational
from medroute.llm import validate_agent_result
from medroute.scenarios import flagship, benchmark_scenarios
from medroute.evaluate import evaluate


def test_audit_chain_detects_tampering():
    history = Sandbox().advance()['audit']
    assert verify(history)['valid']
    tampered = deepcopy(history)
    tampered[0]['detail'] = 'fabricated authorization'
    assert not verify(tampered)['valid']


def test_role_audit_exposes_model_mode():
    data = Sandbox().state()
    assert data['implementation_mode'] == 'deterministic_role_prototypes_no_llm'
    assert data['audit_verification']['valid']


def test_claim_provenance_references_unique_sources():
    refs = {item['id'] for item in catalog()}
    statements = claims()
    assert len(statements) >= 7
    assert len({x['id'] for x in statements}) == len(statements)
    assert all(x['source_id'] in refs for x in statements)


def test_search_returns_source_urls_and_country_scope():
    found = search_claims('UAE authorized commercial medicine suppliers')
    assert found
    assert all(x['url'].startswith('https://') and 'effect' in x for x in found)


def test_no_transfers_are_auto_authorized():
    state = Sandbox().state()
    assert state['release_status'] != 'AUTHORIZED'
    assert state['legal_check']['status'] == 'HUMAN_REVIEW_REQUIRED'
    assert all(t['quantity'] > 0 for t in state['plan']['transfers'])


def test_solver_operational_invariants_on_100_cases():
    for scenario in benchmark_scenarios(count=100, seed=42):
        game = Sandbox(scenario)
        game.advance(); game.advance()
        result = optimize(game.known)
        assert validate_operational(game.world, result)['passes']
        assert all(type(t['quantity']) is int for t in result['transfers'])


def test_reject_route_split_that_exceeds_combined_capacity():
    scenario = flagship()
    proposal = {'transfers': [{'route': 'B-A', 'from': 'Hospital B', 'to': 'Hospital A', 'quantity': 50},
                              {'route': 'B-A', 'from': 'Hospital B', 'to': 'Hospital A', 'quantity': 30}]}
    assert not validate_operational(scenario, proposal)['passes']


def test_llm_cannot_inject_legal_approval_or_fabricated_citations():
    result = validate_agent_result({'summary': 'Suggest reviewing transfers.',
                                   'cited_claim_ids': ['C-EDE-001', 'FAKE-CITATION'],
                                   'legal_status': 'APPROVED', 'autonomous_transfer_authorized': True},
                                  {'C-EDE-001'})
    assert result['cited_claim_ids'] == ['C-EDE-001']
    assert result['legal_status'] == 'HUMAN_REVIEW_REQUIRED'
    assert result['autonomous_transfer_authorized'] is False


def test_evaluation_is_deterministic_and_valid():
    a, b = evaluate(count=30, seed=2026), evaluate(count=30, seed=2026)
    assert a['stats'] == b['stats']
    assert a['stats']['optimized']['operational_valid_rate'] == 1.0
