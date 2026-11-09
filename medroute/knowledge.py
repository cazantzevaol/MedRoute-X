"""Traceable curated policy evidence; never converts source summaries into legal permission.

Only public, manually verified high-level summaries are bundled. The project does
NOT claim ingestion of full UAE statutory texts or case-specific legal clearance.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from .regulatory import transfer_pathway

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / 'kb' / 'sources.json'
CLAIMS_PATH = ROOT / 'kb' / 'claims.json'


def catalog():
    return json.loads(CATALOG_PATH.read_text(encoding='utf-8'))


def claims():
    return json.loads(CLAIMS_PATH.read_text(encoding='utf-8'))


def validate_evidence_integrity(source_items, claim_items):
    """Reject ambiguous or untraceable evidence before it reaches an agent.

    This checks local metadata integrity, NOT the legal truth of source content.
    """
    source_ids = set()
    for source in source_items:
        identifier = source.get('id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in source_ids:
            raise ValueError('Invalid or duplicate evidence source ID')
        source_ids.add(identifier)
        url = source.get('url', '')
        try:
            parsed = urlsplit(url)
            valid_url = (parsed.scheme == 'https' and bool(parsed.hostname)
                         and not parsed.username and not parsed.password
                         and not parsed.fragment and not any(c.isspace() for c in url))
        except (TypeError, ValueError):
            valid_url = False
        if not valid_url:
            raise ValueError(f'Invalid evidence source URL: {identifier}')

    claim_ids = set()
    for claim in claim_items:
        identifier = claim.get('id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in claim_ids:
            raise ValueError('Invalid or duplicate evidence claim ID')
        claim_ids.add(identifier)
        if claim.get('source_id') not in source_ids:
            raise ValueError(f'Claim references missing source: {identifier}')
    return {'sources': len(source_ids), 'claims': len(claim_ids), 'integrity': 'PASS',
            'legal_review': 'NOT_PERFORMED'}


def _tokens(value):
    return re.findall(r'[a-z0-9]+', value.lower().replace('-', ' '))


def evidence_assurance(claim, source):
    """Fail-closed distinction between provenance and *legal applicability*.

    Source-page verification, a matching claim ID, or a 'verified' metadata flag
    never establishes permission for a particular medical-product transfer.
    No legal signoff is issued by this research prototype.
    """
    source_scope = str(source.get('jurisdiction', '')).strip().casefold()
    claim_scope = str(claim.get('jurisdiction', '')).strip().casefold()
    uae_scope = source_scope == 'uae' and claim_scope == 'uae'
    return {
        'source_review_status': str(source.get('legal_review', 'missing')),
        'claim_review_status': str(claim.get('review', 'missing')),
        'legal_applicability': ('UNVERIFIED_UAE_APPLICABILITY' if uae_scope
                                else 'CONTEXT_ONLY_NOT_UAE_LEGAL_BASIS'),
        'legal_clearance': False,
        'human_legal_review_required': True,
    }


def search_claims(query, limit=5, jurisdiction=None):
    """A tiny transparent BM25-style index over curated evidence statements."""
    items = claims()
    source_items = catalog()
    validate_evidence_integrity(source_items, items)
    if jurisdiction:
        items = [item for item in items if item['jurisdiction'].lower() == jurisdiction.lower()]
    if not items:
        return []
    docs = [_tokens(item['claim'] + ' ' + ' '.join(item['topics'])) for item in items]
    df = Counter(term for doc in docs for term in set(doc))
    avg = sum(map(len, docs)) / len(docs)
    q = set(_tokens(query))
    scores = []
    for item, doc in zip(items, docs):
        counts, length, score = Counter(doc), len(doc), 0.0
        for term in q:
            freq = counts.get(term, 0)
            if freq:
                idf = math.log(1 + (len(docs) - df[term] + .5)/(df[term] + .5))
                score += idf * freq * 2.2 / (freq + 1.2 * (.25 + .75 * length / avg))
        if score:
            scores.append((round(score, 4), item))
    source_index = {s['id']: s for s in source_items}
    return [{'score': score, **item, 'url': source_index[item['source_id']]['url'],
             'source_title': source_index[item['source_id']]['title'],
             **evidence_assurance(item, source_index[item['source_id']])}
            for score, item in sorted(scores, key=lambda x: (-x[0], x[1]['id']))[:limit]]


def retrieve(topic):
    """Legacy source-level search retained for backward compatibility."""
    found = search_claims(topic, limit=20)
    sources = {s['id']: s for s in catalog()}
    ordered = []
    for hit in found:
        if hit['source_id'] not in [s['id'] for s in ordered]:
            ordered.append(sources[hit['source_id']])
    return ordered


def permission_verdict(transfers, product_category='unspecified', emergency_declared=False):
    """Default deny: missing product/facility-specific permission remains unknown."""
    pathway = transfer_pathway(transfers, product_category, emergency_declared)
    if not transfers:
        return {'status': 'NOT_APPLICABLE', 'message': 'No transfer proposed.', 'evidence': [],
                'missing': [], 'regulatory_pathway': pathway}
    return {'status': 'HUMAN_REVIEW_REQUIRED',
            'message': 'Candidate movements are NOT approved. Qualified local authorities must verify product registration, facility authority, required permits and distribution conditions. High-level policy announcements do not authorize a transfer.',
            'evidence': ['C-EDE-002', 'C-EDE-001'] + pathway['source_claim_ids'],
            'regulatory_pathway': pathway,
            'missing': ['binding product-specific transfer rule', 'facility-to-facility authorization',
                        'authorized signer and product conditions']}


def gap_hypothesis():
    return {'classification': 'RESEARCH_QUESTION_NOT_VERIFIED_LEGAL_GAP',
            'question': 'What documented inter-institutional data exchange, escalation and transfer approval procedures apply when one facility lacks an essential medicine and information arrives unevenly?',
            'required_evidence': ['full binding UAE transfer and data-sharing texts',
                                  'roles and escalation guidance for relevant institutions',
                                  'qualified legal and pharmacy review'],
            'comparison': 'EMA EU/EEA voluntary solidarity is a comparator; it does not authorize UAE transfers.',
            'references': ['C-EDE-002', 'C-EDE-001', 'C-EMA-001']}
