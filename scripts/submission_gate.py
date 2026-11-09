"""Fail-closed local submission preflight. No network, upload, or legal approval.

Usage: python scripts/submission_gate.py --version 0.10
The output distinguishes a *locally prepared* artifact from external submission.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

REQUIRED_TOPICS = (
    'ITU-T Y.3172',
    'AI Readiness Framework',
    'Evaluation scenario',
    'Policy and standards gaps',
    'Synthetic data',
    'Human authorization',
    '10 November 2026',
)


def reported_test_count(text: str):
    """Return the declared suite size; reject absent or ambiguous claims."""
    counts = re.findall(r'Offline regression suite:\s*(\d+)\s+tests\b', text, re.I)
    return int(counts[0]) if len(counts) == 1 else None


def inspect_pdf(path: Path, version: str, expected_tests=None):
    """Return (page count, findings); fail closed if PDF text cannot be inspected."""
    issues = []
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, ['pypdf missing: cannot verify report page count or text']
    try:
        reader = PdfReader(str(path))
        pages = len(reader.pages)
        content = '\n'.join(page.extract_text() or '' for page in reader.pages)
    except Exception:
        return None, ['PDF cannot be parsed or its text extracted']
    if not 1 <= pages <= 5:
        issues.append(f'Technical report must be 1-5 pages; found {pages}')
    if f'v{version}' not in content:
        issues.append(f'Technical report missing release label v{version}')
    if expected_tests is not None and reported_test_count(content) != expected_tests:
        issues.append(f'Technical report test count is stale or ambiguous; expected {expected_tests}')
    if not content.strip():
        issues.append('Technical report has no extractable text')
    for topic in REQUIRED_TOPICS:
        if topic.casefold() not in content.casefold():
            issues.append(f'Technical report missing topic: {topic}')
    if re.search(r'(?i)\b(?:v0\.4|27 Oct 2026)\b', content):
        issues.append('Technical report contains stale v0.4/date footer')
    return pages, issues


def inspect_knowledge_base(source_path: Path, claim_path: Path):
    issues = []
    try:
        sources = json.loads(source_path.read_text(encoding='utf-8'))
        claims = json.loads(claim_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, None, ['Knowledge base missing or invalid JSON']
    if not isinstance(sources, list) or not isinstance(claims, list):
        return None, None, ['Knowledge base source and claim roots must be arrays']
    ids = [s.get('id') for s in sources if isinstance(s, dict)]
    cids = [c.get('id') for c in claims if isinstance(c, dict)]
    if (len(ids) != len(sources) or
            not all(isinstance(v, str) and v.strip() for v in ids) or
            len(set(v for v in ids if isinstance(v, str))) != len(ids)):
        issues.append('Source identifiers missing, malformed or duplicated')
    if (len(cids) != len(claims) or
            not all(isinstance(v, str) and v.strip() for v in cids) or
            len(set(v for v in cids if isinstance(v, str))) != len(cids)):
        issues.append('Claim identifiers missing, malformed or duplicated')
    if not sources or not claims:
        issues.append('Knowledge base cannot be empty')
    for s in sources:
        if not isinstance(s, dict):
            issues.append('Malformed source record')
            continue
        u = s.get('url', '')
        try:
            parsed = urlsplit(u)
            valid = parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username
        except (TypeError, ValueError):
            valid = False
        if not valid:
            issues.append(f'Invalid HTTPS provenance pointer for {s.get("id", "unknown")}')
        if not s.get('legal_review') or not s.get('ingestion_status'):
            issues.append(f'Missing source review status for {s.get("id", "unknown")}')
    known = {v for v in ids if isinstance(v, str)}
    for c in claims:
        if not isinstance(c, dict):
            issues.append('Malformed claim record')
            continue
        if not isinstance(c.get('source_id'), str) or c['source_id'] not in known:
            issues.append(f'Orphan claim {c.get("id", "unknown")}')
        if not all(c.get(field) for field in ('claim', 'jurisdiction', 'effect', 'review')):
            issues.append(f'Incomplete claim {c.get("id", "unknown")}')
    return len(sources), len(claims), issues


def audit_submission(root: Path, version='0.10', expected_tests=None, expected_sources=None, expected_claims=None):
    root = Path(root)
    pdf = root / 'reports' / 'technical_report.pdf'
    pages, pdf_issues = inspect_pdf(pdf, version, expected_tests)
    ns, nc, kb_issues = inspect_knowledge_base(root / 'kb' / 'sources.json', root / 'kb' / 'claims.json')
    issues = pdf_issues + kb_issues
    if expected_sources is not None and ns != expected_sources:
        issues.append(f'Knowledge base source count differs from verified release: expected {expected_sources}, found {ns}')
    if expected_claims is not None and nc != expected_claims:
        issues.append(f'Knowledge base claim count differs from verified release: expected {expected_claims}, found {nc}')
    if not (root / 'README.md').is_file():
        issues.append('Missing README.md')
    if not (root / 'reports' / 'benchmark_summary.json').is_file():
        issues.append('Missing reproducible benchmark summary')
    if not (root / 'reports' / 'demo_script_en.md').is_file():
        issues.append('Missing demonstration script')
    if not (root / 'tests').is_dir():
        issues.append('Missing automated test suite')
    # Review completeness is reported separately from structural validity.
    # A pending review never becomes a legal approval through this local gate.
    try:
        sources = json.loads((root / 'kb' / 'sources.json').read_text(encoding='utf-8'))
        claims = json.loads((root / 'kb' / 'claims.json').read_text(encoding='utf-8'))
        pending_sources = sum(1 for s in sources if isinstance(s, dict) and str(s.get('legal_review', '')).casefold() not in ('approved', 'verified'))
        pending_claims = sum(1 for c in claims if isinstance(c, dict) and str(c.get('review', '')).casefold() not in ('approved', 'verified'))
    except (OSError, ValueError, TypeError):
        pending_sources = pending_claims = None
    # The tool cannot determine whether a team registered or an external repo exists.
    return {
        'release': version,
        'local_preflight_passed': not issues,
        'report_pages': pages,
        'source_count': ns,
        'claim_count': nc,
        'issues': issues,
        'external_requirements': {
            'registration_or_team_eligibility': 'UNVERIFIED',
            'github_repository_accessible_to_judges': 'UNVERIFIED',
            'organizer_submission': 'NOT_PERFORMED',
            'expert_legal_and_pharmacy_review': 'NOT_PERFORMED',
        },
        'regulatory_evidence': {
            'sources_not_verified': pending_sources,
            'claims_not_verified': pending_claims,
            'expert_signoff': 'NOT_VERIFIED',
            'status': 'REQUIRES_REVIEW',
        },
        'submission_ready': False,
        'notice': 'Local checks do not certify legal compliance, registration or submission.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local-only submission artifact gate')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--version', default='0.10')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expected-tests', type=int, help='Verified pytest count from this release')
    parser.add_argument('--expected-sources', type=int, help='Verified source count')
    parser.add_argument('--expected-claims', type=int, help='Verified claim count')
    args = parser.parse_args(argv)
    result = audit_submission(args.root, args.version, args.expected_tests, args.expected_sources, args.expected_claims)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + '\n', encoding='utf-8')
    print(output)
    return 0 if result['local_preflight_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
