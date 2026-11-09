"""Offline regression tests for the ITU submission artifact gate."""
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from scripts.submission_gate import audit_submission, inspect_pdf, inspect_knowledge_base, REQUIRED_TOPICS


def make_pdf(path, pages=1, text=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path))
    for _ in range(pages):
        c.drawString(50, 750, text)
        c.showPage()
    c.save()


def fixture_root(tmp_path, report_text):
    (tmp_path / 'reports').mkdir()
    (tmp_path / 'kb').mkdir()
    (tmp_path / 'tests').mkdir()
    for file in ('README.md', 'reports/benchmark_summary.json', 'reports/demo_script_en.md'):
        (tmp_path / file).write_text('synthetic only', encoding='utf-8')
    (tmp_path / 'kb/sources.json').write_text(json.dumps([{'id':'A','url':'https://example.org/a','legal_review':'pending','ingestion_status':'metadata_only'}]))
    (tmp_path / 'kb/claims.json').write_text(json.dumps([{'id':'C','source_id':'A','claim':'Summary','jurisdiction':'UAE','effect':'not_permission','review':'pending'}]))
    make_pdf(tmp_path / 'reports/technical_report.pdf', text=report_text)
    return tmp_path


def test_actual_submission_report_is_current():
    root = Path(__file__).resolve().parent.parent
    result = audit_submission(root, version='0.10')
    assert result['local_preflight_passed'], result['issues']
    assert result['report_pages'] == 5
    assert result['submission_ready'] is False
    assert result['external_requirements']['organizer_submission'] == 'NOT_PERFORMED'


def test_stale_report_is_blocked(tmp_path):
    root = fixture_root(tmp_path, 'MEDROUTE X v0.4')
    result = audit_submission(root, '0.10')
    assert not result['local_preflight_passed']
    assert any('v0.10' in x for x in result['issues'])


def test_too_many_pages_is_blocked(tmp_path):
    path = tmp_path / 'too_many.pdf'
    make_pdf(path, pages=6, text='MedRoute X v0.10')
    _, issues = inspect_pdf(path, '0.10')
    assert any('1-5 pages' in x for x in issues)


def test_corrupt_pdf_is_blocked(tmp_path):
    p = tmp_path / 'bad.pdf'
    p.write_bytes(b'not a PDF')
    _, issues = inspect_pdf(p, '0.10')
    assert any('cannot be parsed' in x for x in issues)


def test_missing_report_is_blocked(tmp_path):
    _, issues = inspect_pdf(tmp_path / 'none.pdf', '0.10')
    assert issues


def test_orphan_claim_is_blocked(tmp_path):
    root = fixture_root(tmp_path, 'v0.10')
    path = root / 'kb/claims.json'
    items = json.loads(path.read_text())
    items[0]['source_id'] = 'NOT-FOUND'
    path.write_text(json.dumps(items))
    _, _, issues = inspect_knowledge_base(root / 'kb/sources.json', path)
    assert any('Orphan claim' in x for x in issues)


def test_duplicate_source_is_blocked(tmp_path):
    root = fixture_root(tmp_path, 'v0.10')
    path = root / 'kb/sources.json'
    items = json.loads(path.read_text())
    path.write_text(json.dumps(items + items))
    _, _, issues = inspect_knowledge_base(path, root / 'kb/claims.json')
    assert any('duplicated' in x for x in issues)


def test_untrusted_provenance_url_is_blocked(tmp_path):
    root = fixture_root(tmp_path, 'v0.10')
    path = root / 'kb/sources.json'
    items = json.loads(path.read_text())
    items[0]['url'] = 'http://example.org/a'
    path.write_text(json.dumps(items))
    _, _, issues = inspect_knowledge_base(path, root / 'kb/claims.json')
    assert any('Invalid HTTPS' in x for x in issues)


def test_missing_review_status_is_blocked(tmp_path):
    root = fixture_root(tmp_path, 'v0.10')
    path = root / 'kb/sources.json'
    items = json.loads(path.read_text())
    del items[0]['legal_review']
    path.write_text(json.dumps(items))
    _, _, issues = inspect_knowledge_base(path, root / 'kb/claims.json')
    assert any('review status' in x for x in issues)


def test_missing_required_report_topic_is_blocked(tmp_path):
    root = fixture_root(tmp_path, 'MedRoute X v0.10')
    _, issues = inspect_pdf(root / 'reports/technical_report.pdf', '0.10')
    assert all(any(topic in issue for issue in issues) for topic in REQUIRED_TOPICS)


def test_no_external_confirmation_from_local_files(tmp_path):
    root = fixture_root(tmp_path, 'MedRoute X v0.10')
    result = audit_submission(root)
    assert result['submission_ready'] is False
    assert result['external_requirements']['registration_or_team_eligibility'] == 'UNVERIFIED'


def test_malformed_identifier_fails_closed_without_exception(tmp_path):
    root = fixture_root(tmp_path, 'v0.10')
    source_path = root / 'kb/sources.json'
    sources = json.loads(source_path.read_text())
    sources[0]['id'] = ['not', 'hashable']
    source_path.write_text(json.dumps(sources))
    _, _, issues = inspect_knowledge_base(source_path, root / 'kb/claims.json')
    assert any('malformed' in x for x in issues)
