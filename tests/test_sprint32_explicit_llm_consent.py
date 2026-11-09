"""No accidental paid network calls, including when a key is present."""
import pytest
from medroute.llm import llm_json_request, llm_for_role, LIVE_LLM_OPT_IN
from medroute.council import OpenAIProvider, run_council
from medroute.engine import Sandbox


def test_live_transport_blocked_even_with_key(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-synthetic-key')
    monkeypatch.delenv('MEDROUTE_ENABLE_LIVE_LLM', raising=False)
    with pytest.raises(PermissionError, match='explicit'):
        llm_json_request('test', {'synthetic': True})


def test_live_provider_blocked_even_with_key(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-synthetic-key')
    monkeypatch.delenv('MEDROUTE_ENABLE_LIVE_LLM', raising=False)
    with pytest.raises(PermissionError):
        OpenAIProvider()
    with pytest.raises(PermissionError):
        llm_for_role(Sandbox(), 'Regulator')


def test_invalid_consent_blocked(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-synthetic-key')
    monkeypatch.setenv('MEDROUTE_ENABLE_LIVE_LLM', 'true')
    with pytest.raises(PermissionError):
        OpenAIProvider()


def test_opt_in_does_not_make_network_call_during_construction(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-synthetic-key')
    monkeypatch.setenv('MEDROUTE_ENABLE_LIVE_LLM', LIVE_LLM_OPT_IN)
    provider = OpenAIProvider()
    assert provider.mode == 'openai_live_unverified_responses'


def test_offline_council_unaffected_without_opt_in(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-synthetic-key')
    monkeypatch.delenv('MEDROUTE_ENABLE_LIVE_LLM', raising=False)
    result = run_council(Sandbox(), roles=['Regulator'])
    assert result['provider_mode'] == 'offline_scripted_protocol'
    assert result['artifact_verification']['valid']
