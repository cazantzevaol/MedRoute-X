"""Optional local AI triage over facts from the public synthetic scenario."""
import json
import os
import re
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

URL = 'http://127.0.0.1:11434/api/generate'
MAX_RESPONSE_BYTES = 32768


class BriefingUnavailable(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_briefing(state, *, transport=None):
    model = os.getenv('MEDROUTE_LOCAL_MODEL', '')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*(?::[a-zA-Z0-9][a-zA-Z0-9_.-]*)?', model):
        raise BriefingUnavailable('Set MEDROUTE_LOCAL_MODEL to an installed local Ollama model.')
    if 'cloud' in model.casefold():
        raise BriefingUnavailable('Choose a local Ollama model tag.')
    plan = state['plan']
    facts = {
        'operations': ('The independent operational check passed.' if state['operational_check']['passes']
                       else 'The independent operational check blocked the proposed plan.'),
        'shortfall': (f"The proposed plan leaves {plan['unmet_total']} packs unmet."
                      if state['operational_check']['passes']
                      else f"The blocked plan estimates {plan['unmet_total']} packs unmet; this is not an executable result."),
        'disclosure': ('A supplier update awaits disclosure to the coordinator.' if state.get('pending_supplier_disclosure', state['disruption_pending'])
                       else 'No live supplier update is awaiting disclosure.'),
        'review': 'A human must review any proposed transfer authorization.',
    }
    payload = {
        'model': model, 'stream': False,
        'format': {'type': 'object', 'properties': {'focus': {'enum': list(facts)}},
                   'required': ['focus'], 'additionalProperties': False},
        'system': ('Triage a synthetic medicine logistics exercise. Select the one fact that '
                   'deserves attention first. Prioritize unresolved operational blockers and '
                   'pending disclosures. Return only the requested JSON.'),
        'prompt': json.dumps({'release_status': state['release_status'], 'facts': facts}),
        'options': {'temperature': 0, 'num_predict': 64},
    }
    request = Request(URL, json.dumps(payload).encode(), {'Content-Type': 'application/json'})
    opener = transport or build_opener(ProxyHandler({}), NoRedirect()).open
    try:
        with opener(request, timeout=25) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError('Oversized response')
        envelope = json.loads(raw)
        if not isinstance(envelope, dict):
            raise ValueError('Invalid envelope')
        decision = json.loads(envelope['response'])
        if not isinstance(decision, dict) or envelope.get('done') is not True or set(decision) != {'focus'} or decision['focus'] not in facts:
            raise ValueError('Invalid focus')
    except (URLError, TimeoutError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise BriefingUnavailable('Local AI unavailable or returned an invalid result. Check Ollama and the installed model.') from exc
    return {'focus': decision['focus'], 'finding': facts[decision['focus']], 'step': state['step']}
