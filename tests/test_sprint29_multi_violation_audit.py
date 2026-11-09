"""Independent audit signals must not be lost when redaction causes overlap."""
from medroute.llm import validate_agent_result


def test_simultaneous_unsafe_approval_and_forged_citation():
    result = validate_agent_result({
        'summary': 'I approve this transfer now',
        'cited_claim_ids': ['forged'],
        'open_questions': [],
    }, {'legitimate'})
    assert result['safety_flags'] == [
        'unsafe_approval_language_redacted', 'unrecognized_evidence_reference']
    assert result['safety_flag'] == 'unsafe_approval_language_redacted'
    assert result['unrecognized_reference_count'] == 1
    assert 'withheld' in result['summary']
    assert result['autonomous_transfer_authorized'] is False


def test_question_violation_and_forged_citation_both_logged():
    result = validate_agent_result({
        'summary': 'A synthetic scenario',
        'cited_claim_ids': ['forged'],
        'open_questions': ['Permission granted to ship now'],
    }, set())
    assert len(result['safety_flags']) == 2
    assert result['open_questions'] == []


def test_clean_and_single_violation_audit():
    base = {'summary': 'Synthetic scenario', 'cited_claim_ids': [], 'open_questions': []}
    assert validate_agent_result(base, set())['safety_flags'] == []
    forged = dict(base, cited_claim_ids=['fake'])
    assert validate_agent_result(forged, set())['safety_flags'] == ['unrecognized_evidence_reference']
    unsafe = dict(base, summary='I authorize transfer')
    assert validate_agent_result(unsafe, set())['safety_flags'] == ['unsafe_approval_language_redacted']
