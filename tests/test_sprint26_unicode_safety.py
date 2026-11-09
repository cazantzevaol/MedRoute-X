"""Synthetic red-team cases: obfuscated authorization text must not be displayed."""
import pytest
from medroute.llm import validate_agent_result


@pytest.mark.parametrize('text', [
    'I au\u200bthorize this transfer now',
    'permission is gr\u200banted',
    'I ａｐｐｒｏｖｅ the shipment',
    'разре\u200bшаю перевозку',
    'يمكنك \u200bنقل',
])
def test_obfuscated_approval_summary_is_withheld(text):
    result = validate_agent_result({'summary': text}, set())
    assert result['safety_flag'] == 'unsafe_approval_language_redacted'
    assert text not in result['summary']
    assert result['autonomous_transfer_authorized'] is False


@pytest.mark.parametrize('text', [
    'I au\u200bthorize this transfer now',
    'permission is gr\u200banted',
    'разре\u200bшаю перевозку',
])
def test_obfuscated_approval_question_is_withheld(text):
    result = validate_agent_result({'summary': 'Review required', 'open_questions': [text]}, set())
    assert result['safety_flag'] == 'unsafe_approval_language_redacted'
    assert text not in result['open_questions']


def test_benign_unicode_text_remains_readable():
    text = 'Review temperature logs before transfer — human review required.'
    result = validate_agent_result({'summary': text}, set())
    assert result['summary'] == text
    assert result['safety_flag'] == 'none'
