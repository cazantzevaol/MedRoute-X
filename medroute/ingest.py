"""Optional local evidence-corpus preparation for documents the user may lawfully use.

Documents are indexed for retrieval, NOT silently promoted into verified law.
No web crawling, uploads, embedding API calls or automatic legal verdicts.
"""
from __future__ import annotations
import hashlib
import json
import re
from collections import Counter
from math import log
from pathlib import Path
from urllib.parse import urlsplit
import ipaddress



# Deliberately conservative *screening*, not a privacy classifier.  Never put
# matching content into error messages, logs, or the chunk index.
PUBLIC_DOCUMENT_TYPES = frozenset({
    'policy', 'law', 'strategy', 'guidance', 'standard', 'public_service', 'research',
})
PATIENT_FIELD = re.compile(
    r"\b(?:patient(?:['’]s)?[ _-]*(?:full[ _-]*)?name|"
    r"patient[ _-]*id|mrn|medical[ _-]*record[ _-]*(?:number|no\.?)|"
    r"date[ _-]*of[ _-]*birth|dob|emirates[ _-]*id|"
    r"prescription[ _-]*(?:number|no\.?)|"
    r"patient[ _-]*(?:email|phone|mobile))\s*[:=]\s*\S",
    flags=re.IGNORECASE,
)
# UAE ID shape: no value is ever retained or echoed by the screening error.
EMIRATES_ID_SHAPE = re.compile(r'(?<!\d)784-\d{4}-\d{7}-\d(?!\d)')


def _assert_public_policy_text(text):
    if PATIENT_FIELD.search(text) or EMIRATES_ID_SHAPE.search(text):
        raise ValueError('Possible patient-specific information: ingestion blocked; '
                         'use public policy documents only')


def _validate_provenance_url(url):
    """Basic HTTPS syntax check, NOT verification of publisher authenticity."""
    if not isinstance(url, str):
        raise ValueError('A public HTTPS source URL is required')
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError('Invalid public HTTPS source URL') from exc
    if (parsed.scheme != 'https' or not host or parsed.username is not None or
            parsed.password is not None or parsed.fragment or port not in (None, 443) or
            not host.count('.') or host.endswith(('.local', '.internal')) or
            host in ('localhost',) or any(c.isspace() for c in url)):
        raise ValueError('Invalid public HTTPS source URL')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('IP addresses are not accepted as public HTTPS provenance URLs')
    # Caller-supplied URLs are *not* certified as official by this validation.


def chunk_text(text: str, target: int = 1100, overlap: int = 160):
    if not 100 <= overlap < target:
        raise ValueError('overlap must be >= 100 and smaller than target')
    normalized = re.sub(r'[ \t]+', ' ', text.replace('\r\n', '\n')).strip()
    if not normalized:
        return []
    chunks = []
    at = 0
    while at < len(normalized):
        end = min(len(normalized), at + target)
        if end < len(normalized):
            split = max(normalized.rfind('\n', at + target // 2, end),
                        normalized.rfind('. ', at + target // 2, end))
            if split > at + target // 2:
                end = split + (2 if normalized[split:split+2] == '. ' else 1)
        if end <= at:
            end = min(len(normalized), at + target)
        chunks.append(normalized[at:end].strip())
        if end == len(normalized):
            break
        at = max(at+1, end-overlap)
    return [part for part in chunks if part]


def pages_from_file(path):
    path = Path(path)
    if path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError('PDF ingestion needs optional dependency: pip install pypdf') from exc
        reader = PdfReader(str(path))
        for number, page in enumerate(reader.pages, 1):
            yield number, page.extract_text() or ''
    elif path.suffix.lower() in ('.txt', '.md'):
        yield 1, path.read_text(encoding='utf-8')
    else:
        raise ValueError('Only local .pdf, .txt and .md documents are supported')


def ingest_file(path, *, source_id, title, jurisdiction, url, document_type='policy', reviewed=False):
    """Prepare public regulatory material, rejecting obvious patient-record fields.

    This is a screening gate, NOT a guarantee that all identifiers are detected.
    Documents must be checked by a human before ingestion. Even with
    ``reviewed=True``, source URL authenticity and legal accuracy are unverified.
    """
    path = Path(path)
    if (not isinstance(source_id, str) or
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', source_id)):
        raise ValueError('Invalid source_id; use a short public identifier')
    if not isinstance(title, str) or not title.strip():
        raise ValueError('A public document title is required')
    if not isinstance(jurisdiction, str) or not jurisdiction.strip():
        raise ValueError('A jurisdiction is required')
    if not isinstance(document_type, str) or document_type not in PUBLIC_DOCUMENT_TYPES:
        raise ValueError('Only public policy/regulatory document types are accepted')
    if type(reviewed) is not bool:
        raise ValueError('reviewed must be a boolean, not an external approval')
    _validate_provenance_url(url)
    _assert_public_policy_text(title + '\n' + jurisdiction)
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    pages = list(pages_from_file(path))
    if not any(content.strip() for _, content in pages):
        raise ValueError('Document has no extractable text; no chunks indexed')
    # Screen *all* pages before returning *any* chunks. Avoid partial ingestion.
    for _, content in pages:
        _assert_public_policy_text(content)
    out = []
    for page, content in pages:
        for i, chunk in enumerate(chunk_text(content), 1):
            out.append({'id': f'{source_id}:p{page}:c{i}', 'source_id': source_id,
                        'title': title, 'jurisdiction': jurisdiction, 'url': url,
                        'document_type': document_type, 'page': page,
                        'sha256': fingerprint, 'text': chunk,
                        'review_status': ('user_attested_review_not_independently_verified'
                                          if reviewed else 'unverified_extraction'),
                        'source_url_verified': False,
                        'can_authorize_action': False})
    return out


def search_chunks(query, index, limit=6):
    """Simple reproducible BM25 ranking over local document chunks."""
    if limit < 1 or not index:
        return []
    def toks(text): return re.findall(r'[\w]+', text.lower(), flags=re.UNICODE)
    words = set(toks(query))
    documents = [toks(row['text']) for row in index]
    df = Counter(t for doc in documents for t in set(doc))
    avg = sum(len(d) for d in documents) / len(documents)
    matches = []
    for row, tokens in zip(index, documents):
        freq = Counter(tokens)
        score = 0.0
        for term in words:
            if freq[term]:
                idf = log(1 + (len(index)-df[term]+.5)/(df[term]+.5))
                score += idf * freq[term] * 2.2 / (freq[term] + 1.2*(.25+.75*len(tokens)/avg))
        if score:
            matches.append((score, row))
    return [dict(row, relevance=round(score, 4)) for score,row in
            sorted(matches, key=lambda item: (-item[0], item[1]['id']))[:limit]]


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Index an authorized local legal/policy PDF, TXT or MD')
    parser.add_argument('path')
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--jurisdiction', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', default='kb/ingested_chunks.json')
    args = parser.parse_args()
    dest = Path(args.output)
    existing = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else []
    incoming = ingest_file(args.path, source_id=args.source_id, title=args.title,
                           jurisdiction=args.jurisdiction, url=args.url)
    existing = [x for x in existing if x['source_id'] != args.source_id]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(existing+incoming, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Indexed {len(incoming)} chunks to {dest}. Status: UNVERIFIED; human review required.')

if __name__ == '__main__':
    main()
