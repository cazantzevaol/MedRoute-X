"""Hash-chained, inspectable decisions log. It records summaries, never private model CoT."""
import hashlib
import json

GENESIS = '0' * 64


def entry_hash(entry):
    payload = {key: entry[key] for key in ('event_no', 'step', 'kind', 'detail', 'prev_hash')}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def append(chain, step, kind, detail):
    entry = {'event_no': len(chain) + 1, 'step': step, 'kind': kind,
             'detail': detail, 'prev_hash': chain[-1]['hash'] if chain else GENESIS}
    entry['hash'] = entry_hash(entry)
    chain.append(entry)
    return entry


def verify(chain):
    for i, entry in enumerate(chain):
        try:
            if entry['event_no'] != i + 1 or entry['prev_hash'] != (chain[i-1]['hash'] if i else GENESIS):
                return {'valid': False, 'error_at': i + 1}
            if entry.get('hash') != entry_hash(entry):
                return {'valid': False, 'error_at': i + 1}
        except (TypeError, KeyError, ValueError):
            return {'valid': False, 'error_at': i + 1}
    return {'valid': True, 'entries': len(chain), 'head': chain[-1]['hash'] if chain else GENESIS}
