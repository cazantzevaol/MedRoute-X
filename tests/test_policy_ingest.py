"""Extra evidence, audit, policy and corpus quality tests."""
import json
from pathlib import Path
from medroute.engine import Sandbox
from medroute.policy import evidence_dossier, policy_matrix
from medroute.ingest import chunk_text, ingest_file, search_chunks
from medroute.audit import verify


def test_policy_gaps_not_wrongly_asserted():
    s=Sandbox().state()
    rows=s['policy_matrix']['rows']
    assert s['policy_matrix']['confirmed_legal_gaps']==0
    assert all(row['is_confirmed_legal_gap'] is False for row in rows)
    assert any(row['status']=='EVIDENCE_MISSING' for row in rows)


def test_incident_disclosure_changes_gap_review_status():
    engine=Sandbox()
    assert engine.state()['policy_matrix']['rows'][1]['status']=='NOT_TRIGGERED'
    engine.advance()
    assert engine.state()['policy_matrix']['rows'][1]['status']=='REVIEW_REQUIRED'


def test_export_dossier_preserves_references_and_approval_gate():
    s=Sandbox().advance()
    dossier=evidence_dossier(s)
    assert dossier['audit_verification']['valid']
    assert dossier['automated_approval_granted'] is False
    assert dossier['legal_review']['status']=='HUMAN_REVIEW_REQUIRED'
    assert all('https://' in row['source']['url'] for row in dossier['claim_references'])


def test_dashboard_refresh_does_not_modify_hash_chain():
    engine=Sandbox()
    a=engine.state()['audit']; b=engine.state()['audit']
    assert a==b and verify(a)['valid']
    engine.advance()
    assert verify(engine.state()['audit'])['valid']
    assert len(engine.state()['audit']) > len(a)


def test_local_document_ingestion_keeps_page_provenance(tmp_path):
    source=tmp_path/'sample.txt'
    source.write_text('Supply shortage procedures and authorized reporting channels.\n'*60,encoding='utf-8')
    chunks=ingest_file(source,source_id='D-EXAMPLE',title='Test document',jurisdiction='Test',url='https://example.org/test')
    assert len(chunks)>=2
    assert all(x['review_status']=='unverified_extraction' and not x['can_authorize_action'] for x in chunks)
    found=search_chunks('authorized reporting channels',chunks)
    assert found and found[0]['source_id']=='D-EXAMPLE'
    assert chunks[0]['sha256']==chunks[-1]['sha256']


def test_empty_chunks_and_invalid_meta(tmp_path):
    assert chunk_text('')==[]
    doc=tmp_path/'p.md';doc.write_text('hello')
    try: ingest_file(doc,source_id='x',title='x',jurisdiction='UAE',url='http://unsafe')
    except ValueError: pass
    else: raise AssertionError('Expected validation error')
