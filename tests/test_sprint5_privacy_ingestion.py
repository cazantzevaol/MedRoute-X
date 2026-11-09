"""Sprint 5: policy corpus must never become an intake channel for patient records.

All apparent identifiers below are invented fixtures; no patient data is used.
"""
from pathlib import Path
import json

import pytest

from medroute.ingest import ingest_file


SOURCE = dict(source_id='EDE-SYNTH-TEST', title='Synthetic public-policy excerpt',
              jurisdiction='UAE', url='https://ede.gov.ae/en/w/approve-emergency-drugs-and-psychotropic-materials')


def ingest_text(tmp_path, text, **kwargs):
    p = tmp_path / 'public_policy.txt'
    p.write_text(text, encoding='utf-8')
    return ingest_file(p, **(SOURCE | kwargs))


@pytest.mark.parametrize('text', [
    'Patient Name: Example Testperson\nClinical note: synthetic only.',
    'patient_name = Example Testperson\nNo real person.',
    'MRN: DEMO-12345',
    'Medical record number: FAKE-987',
    'Patient ID: SIM-1000',
    'Date of Birth: 2000-01-01',
    'DOB: 2000-01-01',
    'Emirates ID: 784-0000-0000000-0',
    'Prescription Number: DEMO-999',
    'Patient email: sample@example.invalid',
    'Patient phone: 000-000-0000',
])
def test_patient_specific_fields_rejected_without_echo(tmp_path, text):
    with pytest.raises(ValueError, match='patient-specific') as exc:
        ingest_text(tmp_path, text)
    assert 'Testperson' not in str(exc.value)
    assert 'DEMO-12345' not in str(exc.value)


@pytest.mark.parametrize('document_type', ['patient_record', 'prescription', 'clinical_note', 'discharge_summary', 'medical_record'])
def test_clinical_document_types_rejected(tmp_path, document_type):
    with pytest.raises(ValueError, match='public policy'):
        ingest_text(tmp_path, 'No obvious personal data', document_type=document_type)


def test_public_ede_checklist_mentions_patient_requirements_without_patient_data(tmp_path):
    text = ('Official EDE emergency transfer service: patient name, prescription and medical '
            'report are required in the official channel. Do not upload patient data here.\n') * 15
    chunks = ingest_text(tmp_path, text, document_type='public_service')
    assert chunks and all(not row['can_authorize_action'] for row in chunks)
    assert all(row['review_status'] == 'unverified_extraction' for row in chunks)
    assert all(row['source_url_verified'] is False for row in chunks)


def test_synthetic_law_excerpt_keeps_hash_and_page_provenance(tmp_path):
    text = ('Public regulation describing product registration, responsible authorities, '
            'and facility licensing.\n') * 25
    chunks = ingest_text(tmp_path, text, document_type='law')
    assert chunks and all(len(row['sha256']) == 64 for row in chunks)
    assert all(row['page'] == 1 and row['document_type'] == 'law' for row in chunks)
    assert all(row['review_status'] == 'unverified_extraction' for row in chunks)


@pytest.mark.parametrize('url', [
    'https://ede.gov.ae@untrusted.example/doc',
    'https://127.0.0.1/private',
    'https://localhost/notes',
    'https://example.local/notes',
    'https://example.org:8443/doc',
    'https://example.org/doc#secret',
    'http://ede.gov.ae/en/doc',
])
def test_spoofed_or_unsafe_source_urls_rejected(tmp_path, url):
    with pytest.raises(ValueError, match='HTTPS'):
        ingest_text(tmp_path, 'Public policy text only.', url=url)


def test_user_review_flag_cannot_claim_independent_verification(tmp_path):
    chunks = ingest_text(tmp_path, 'Public regulatory information.', reviewed=True)
    assert chunks
    assert all(row['review_status'] == 'user_attested_review_not_independently_verified'
               for row in chunks)
    assert all(row['source_url_verified'] is False for row in chunks)


def test_non_boolean_review_flag_is_rejected(tmp_path):
    with pytest.raises(ValueError, match='reviewed'):
        ingest_text(tmp_path, 'Public regulatory information.', reviewed='yes')


def test_sensitive_fields_in_later_text_block_reject_entire_document(tmp_path):
    text = ('General public law excerpt.\n' * 100) + 'MRN: DEMO-001\n'
    with pytest.raises(ValueError, match='patient-specific'):
        ingest_text(tmp_path, text)


def test_empty_or_nonextractable_document_fails_closed(tmp_path):
    with pytest.raises(ValueError, match='extractable'):
        ingest_text(tmp_path, '   \n  ')


def test_sensitive_source_metadata_rejected(tmp_path):
    with pytest.raises(ValueError, match='source_id'):
        ingest_text(tmp_path, 'Public regulation.', source_id='../../Patient-ID')


def test_public_policy_document_cannot_authorize_medicine_transfer(tmp_path):
    rows = ingest_text(tmp_path, 'Approval workflow is described by the EDE public page.')
    assert all(row['can_authorize_action'] is False for row in rows)


def test_official_health_ict_articles_linked_to_policy_questions():
    from medroute.knowledge import catalog, claims
    from medroute.policy import policy_matrix
    from medroute.engine import Sandbox
    src = next(s for s in catalog() if s['id'] == 'UAE-HEALTHICT-2019')
    assert src['url'] == 'https://uaelegislation.gov.ae/en/legislations/1209/download'
    linked = {c['id']: c for c in claims() if c['source_id'] == src['id']}
    assert linked['C-UAE-HEALTHICT-001']['articles'] == ['4', '16']
    assert linked['C-UAE-HEALTHICT-002']['articles'] == ['13']
    rows = policy_matrix(Sandbox().state()['plan'], [], 0)['rows']
    privacy = next(row for row in rows if row['id'] == 'P-04')
    assert set(linked).issubset(privacy['references'])
    assert privacy['is_confirmed_legal_gap'] is False


def test_legal_article_claims_never_change_authorization_gate():
    from medroute.knowledge import permission_verdict
    proposed = [{'from':'Hospital B','to':'Hospital A','quantity':1}]
    result = permission_verdict(proposed)
    assert result['status'] == 'HUMAN_REVIEW_REQUIRED'
    assert result['regulatory_pathway']['authorization_granted'] is False


def test_sensitive_cli_input_does_not_overwrite_existing_index(tmp_path, monkeypatch):
    from medroute import ingest
    import sys
    source = tmp_path / 'local_policy.txt'
    source.write_text('MRN: DEMO-12345', encoding='utf-8')
    output = tmp_path / 'index.json'
    original = '[{"id":"KEEP-ME"}]'
    output.write_text(original, encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['ingest', str(source), '--source-id', 'D-1',
        '--title', 'Public law', '--jurisdiction', 'UAE', '--url', 'https://example.org/law',
        '--output', str(output)])
    with pytest.raises(ValueError, match='patient-specific'):
        ingest.main()
    assert output.read_text(encoding='utf-8') == original


def test_two_editorial_privacy_retrieval_queries_reproducible():
    from medroute.retrieval_eval import evaluate_retrieval
    path = 'benchmarks/policy_retrieval_sprint5_gold.json'
    first = evaluate_retrieval(path)
    assert first == evaluate_retrieval(path)
    assert first['n'] == 2
    assert first['hit_at_1'] == 1.0
