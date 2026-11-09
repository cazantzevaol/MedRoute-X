"""Offline synthetic adversarial checks for evidence laundering."""
import pytest
from medroute.llm import validate_agent_result

@pytest.mark.parametrize("refs", [
    ["FAKE"], ["KNOWN", "FAKE"], ["KNOWN"] * 20 + ["FAKE"], [None], [42],
])
def test_unrecognized_evidence_withholds_entire_narrative(refs):
    r = validate_agent_result({
        "summary": "This synthetic transfer is compliant with every rule.",
        "cited_claim_ids": refs,
        "open_questions": ["No regulatory review needed."],
    }, {"KNOWN"})
    assert "compliant with every rule" not in r["summary"]
    assert "withheld" in r["summary"]
    assert r["open_questions"] == []
    assert all(ref == "KNOWN" for ref in r["cited_claim_ids"])
    assert r["citation_integrity"] == "UNRECOGNIZED_REFERENCES"
    assert r["unrecognized_reference_count"] >= 1
    assert r["autonomous_transfer_authorized"] is False

def test_clean_reference_keeps_narrative_but_not_legal_approval():
    r = validate_agent_result({"summary": "Human review needed",
                               "cited_claim_ids": ["KNOWN"],
                               "open_questions": ["Which rule applies?"]}, {"KNOWN"})
    assert r["summary"] == "Human review needed"
    assert r["open_questions"] == ["Which rule applies?"]
    assert r["cited_claim_ids"] == ["KNOWN"]
    assert r["evidence_entailment_verified"] is False
    assert r["legal_status"] == "HUMAN_REVIEW_REQUIRED"

def test_combined_unsafe_approval_and_forged_reference_keeps_both_indicators():
    r = validate_agent_result({"summary": "I authorize transfer now",
                               "cited_claim_ids": ["FAKE"]}, set())
    assert r["safety_flag"] == "unsafe_approval_language_redacted"
    assert r["citation_integrity"] == "UNRECOGNIZED_REFERENCES"
    assert r["cited_claim_ids"] == []
