"""Tests for safety invariants, partial knowledge, and reproducibility."""
from copy import deepcopy
import pytest
from medroute.scenarios import flagship, benchmark_scenarios
from medroute.engine import Sandbox
from medroute.optimizer import compute_needs, optimize, validate_operational
from medroute.knowledge import catalog, permission_verdict, gap_hypothesis, retrieve
from medroute.agents import ROLES, observe
from medroute.evaluate import evaluate


def test_ten_distinct_role_names():
    assert len(ROLES) == len(set(ROLES)) == 10


def test_initial_plan_pending_human_authorization():
    state = Sandbox().state()
    assert state["release_status"] == "PENDING_AUTHORIZATION"
    assert state["legal_check"]["status"] == "HUMAN_REVIEW_REQUIRED"


def test_first_event_is_not_shared_with_coordinator():
    game = Sandbox()
    old = next(r["capacity"] for r in game.known["routes"] if r["id"] == "B-A")
    after = game.advance()
    assert next(r["capacity"] for r in game.known["routes"] if r["id"] == "B-A") == old
    assert after["release_status"] == "BLOCKED_OPERATIONAL"
    assert after["operational_check"]["issues"]
    from medroute.review_packet import review_packet
    before = deepcopy(vars(game))
    packet = review_packet(game)
    assert vars(game) == before
    assert len(packet['alternatives']) == 3
    assert packet['next_action']['owner'] == 'Supplier / Coordinator'
    assert packet['alternatives'][2]['operational_pass'] is False
    chosen = next(option for option in packet['alternatives']
                  if option['method'] == packet['recommendation']['method'])
    assert chosen['operational_pass']
    assert packet['recommendation']['provisional']
    assert packet['recommendation']['additional_supply_requests']
    assert packet['recommendation']['transfer_authorized'] is False
    assert all(option['transfer_authorized'] is False for option in packet['alternatives'])
    game.advance()
    assert review_packet(game)['alternatives'][2]['operational_pass'] is True


def test_supplier_knows_capacity_before_coordinator():
    game = Sandbox()
    game.advance()
    supplier = observe(game.known, "Supplier", game.reports, 1)
    coord = observe(game.known, "Coordinator", game.reports, 1)
    assert supplier["routes"][0]["capacity"] == 15
    assert coord["routes"][0]["capacity"] == 70
    assert supplier["received_reports"] and not coord["received_reports"]


def test_second_event_removes_stale_capacity_issue():
    game = Sandbox(); game.advance(); after = game.advance()
    assert after["operational_check"]["passes"]
    assert after["release_status"] == "PENDING_AUTHORIZATION"
    assert after["plan"]["unmet_total"] > 0


def test_no_route_can_exceed_capacity():
    s = flagship()
    plan = optimize(s)
    assert validate_operational(s, plan)["passes"]


def test_temperature_constraint_rejects_route():
    s = flagship()
    s["routes"][0]["temperature_ok"] = False
    plan = optimize(s)
    assert not any(t["route"] == "B-A" for t in plan["transfers"])


def test_synthetic_inventory_not_negative():
    need, spare = compute_needs(flagship())
    assert all(x>=0 for x in need.values())
    assert all(x>=0 for x in spare.values())


def test_invalid_live_fact_is_caught_by_independent_validator():
    s = flagship(); plan = optimize(s)
    changed = deepcopy(s)
    changed["routes"][0]["capacity"] = 0
    result = validate_operational(changed, plan)
    assert not result["passes"]


def test_authorization_never_automatically_issued():
    permission = permission_verdict(optimize(flagship())["transfers"])
    assert permission["status"] == "HUMAN_REVIEW_REQUIRED"


def test_empty_transfer_does_not_request_approval():
    assert permission_verdict([])["status"] == "NOT_APPLICABLE"


def test_gap_is_not_claimed_as_established_law():
    assert gap_hypothesis()["classification"] == "RESEARCH_QUESTION_NOT_VERIFIED_LEGAL_GAP"


def test_sources_have_traceable_urls():
    sources = catalog()
    assert len(sources) >= 5
    assert len(set(x["id"] for x in sources)) == len(sources)
    assert all(x["url"].startswith("https://") for x in sources)
    assert retrieve("medicine")


def test_no_personal_patient_data():
    s = flagship(); assert all("patient" not in str(key).lower() for x in s["sites"] for key in x)
    assert Sandbox().state()["no_patient_data"]


def test_repeatability_of_30_cases():
    a, b = benchmark_scenarios(), benchmark_scenarios()
    assert a == b and len(a) == 30


def test_baseline_comparison_is_not_fabricated():
    result = evaluate()
    assert result["stats"]["optimized"]["scenarios"] == 30
    assert all(r["operational_valid"] for r in result["records"])
    assert all(r["legal_approval"] == "not_granted_by_demo" for r in result["records"])


def test_final_event_has_no_hidden_changes():
    game = Sandbox(); game.advance(); game.advance()
    snapshot = game.state()
    again = game.advance()
    assert again["step"] == snapshot["step"]


def test_failed_calculation_leaves_advance_and_reset_retryable(monkeypatch):
    from copy import deepcopy
    import medroute.engine as engine

    game = Sandbox()
    game.advance()
    before = deepcopy(vars(game))

    def fail_calculation(scenario):
        raise RuntimeError('synthetic calculation failure')

    import pytest
    with monkeypatch.context() as patch:
        patch.setattr(engine, 'optimize', fail_calculation)
        with pytest.raises(RuntimeError):
            game.advance()
        assert vars(game) == before
        with pytest.raises(RuntimeError):
            game.reset()
        assert vars(game) == before

    assert game.advance()['step'] == 2
    assert game.state()['audit_verification']['valid']
    assert game.reset()['step'] == 0
