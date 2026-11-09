"""Sprint 5 independent acceptance checks (offline, synthetic-only)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from medroute.engine import Sandbox
from medroute.ingest import ingest_file
from medroute.knowledge import catalog, claims, permission_verdict
from medroute.policy import policy_matrix
from medroute.coverage import report as coverage_report



def main():
    checks = {}
    with TemporaryDirectory(prefix='medroute_sprint5_') as temp:
        path = Path(temp) / 'synthetic_public_policy.txt'
        params = dict(source_id='SYNTH-001', title='Synthetic policy text',
                      jurisdiction='UAE', url='https://example.org/policy', document_type='policy')
        path.write_text('Public health data governance guidance. ' * 60, encoding='utf-8')
        chunks = ingest_file(path, **params)
        checks['public_text_indexed_without_authorization'] = bool(chunks) and all(
            not row['can_authorize_action'] and row['source_url_verified'] is False for row in chunks)
        path.write_text('MRN: DEMO-12345\n' + ('Public text. ' * 200), encoding='utf-8')
        try:
            ingest_file(path, **params)
        except ValueError as exc:
            checks['patient_record_field_blocked_without_echo'] = ('patient-specific' in str(exc) and
                                                                     'DEMO-12345' not in str(exc))
        else:
            checks['patient_record_field_blocked_without_echo'] = False
        try:
            ingest_file(path, **(params | {'url': 'https://ede.gov.ae@untrusted.example/doc'}))
        except ValueError:
            checks['spoofed_provenance_url_rejected'] = True
        else:
            checks['spoofed_provenance_url_rejected'] = False

    sources = {x['id']: x for x in catalog()}
    statement_ids = {x['id'] for x in claims()}
    checks['health_ict_official_articles_referenced'] = (
        sources.get('UAE-HEALTHICT-2019', {}).get('url') ==
        'https://uaelegislation.gov.ae/en/legislations/1209/download' and
        {'C-UAE-HEALTHICT-001', 'C-UAE-HEALTHICT-002'}.issubset(statement_ids))
    state = Sandbox().state()
    privacy_row = next(x for x in policy_matrix(state['plan'], [], 0)['rows'] if x['id'] == 'P-04')
    checks['privacy_policy_question_has_article_citations'] = (
        {'C-UAE-HEALTHICT-001', 'C-UAE-HEALTHICT-002'}.issubset(privacy_row['references']) and
        not privacy_row['is_confirmed_legal_gap'])
    verdict = permission_verdict([{'from':'Hospital B','to':'Hospital A','quantity':1}])
    checks['independent_legal_gate_still_denies'] = (
        verdict['status'] == 'HUMAN_REVIEW_REQUIRED' and
        verdict['regulatory_pathway']['authorization_granted'] is False)
    cov = coverage_report()
    checks['new_coverage_category_present'] = (
        'health_information_confidentiality' in cov['category_coverage'] and
        cov['source_count'] == len(sources) and cov['claim_count'] == len(statement_ids))
    output = {
        'date': '2026-10-31', 'version': '0.9.0', 'source_version': '0.8.0',
        'checks': checks, 'passed': sum(checks.values()), 'total': len(checks),
        'success': all(checks.values()),
        'limitations': [
            'No real patient data; only invented field-value examples used.',
            'Privacy screening detects common patterns only; manual document vetting remains mandatory.',
            'Official English law excerpts are not a qualified Arabic-language legal opinion.',
            'No live LLM calls, no regulatory approvals, no publication or submission.',
        ]
    }
    destination = ROOT / 'reports' / 'sprint5_acceptance.json'
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if not output['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
