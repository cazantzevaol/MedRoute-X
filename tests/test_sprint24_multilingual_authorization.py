"""Offline regression tests for unsafe model-generated approval statements."""
import pytest
from medroute.llm import validate_agent_result

@pytest.mark.parametrize('summary', [
    'Permission granted to transfer the medicine.',
    'Authorization is granted for dispatch.',
    'You may now transfer the stock.',
    'The facility can ship these medicines.',
    'Cleared to dispatch immediately.',
    'Разрешаю перевозку лекарств.',
    'Одобрено передачу лекарств.',
    'يمكنك نقل الأدوية.',
])
def test_multilingual_approval_redacted(summary):
    result = validate_agent_result({'summary': summary, 'cited_claim_ids': []}, set())
    assert result['safety_flag'] == 'unsafe_approval_language_redacted'
    assert summary not in result['summary']
    assert result['autonomous_transfer_authorized'] is False
    assert result['legal_status'] == 'HUMAN_REVIEW_REQUIRED'

@pytest.mark.parametrize('summary', [
    'Permission is not granted for any transfer.',
    'No authority to approve a transfer is established.',
    'Qualified counsel must review the proposed transfer.',
])
def test_cautious_language_preserved(summary):
    result = validate_agent_result({'summary': summary}, set())
    assert result['summary'] == summary
    assert result['safety_flag'] == 'none'
