"""Prove CI's agent automation is deterministic, honest and fail-closed."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('agent_review', ROOT/'scripts'/'agent_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def test_invalid_findings_rejected():
    import pytest
    with pytest.raises(ValueError):
        review.finding('Test', 'unknown', 'incorrect status')


def test_protocol_agent_keeps_human_control():
    finding = review.protocol_agent()
    assert finding['status'] == 'pass'
    assert [x['step'] for x in finding['evidence']['states']] == [0, 1, 2]
    assert all(x['no_agent_authorizations'] for x in finding['evidence']['states'])
    assert all(x['audit_valid'] for x in finding['evidence']['states'])
    assert finding['evidence']['disclosure_alert_pattern'] == [False, True, False, True, False]
    assert finding['evidence']['public_redaction_ok'] is True


def test_knowledge_agent_does_not_claim_full_laws():
    finding = review.knowledge_agent()
    assert finding['status'] in ('warning', 'fail')
    assert finding['evidence']['national_full_text_complete'] is False
    assert finding['evidence']['expert_review_complete'] is False


def test_scientific_agent_does_not_fabricate_live_research():
    f = review.research_agent()
    assert f['evidence']['live_web_research_performed'] is False
    assert f['evidence']['official_jury_score'] is None


def test_benchmark_has_same_number_cases_and_no_approvals():
    f = review.benchmark_agent(5)
    assert f['status'] == 'pass'
    assert f['evidence']['case_count'] == 5
    assert f['evidence']['operational_valid_all'] is True


def test_full_report_has_agent_evidence_without_false_success(monkeypatch):
    # Avoid running entire pytest suite recursively inside pytest.
    monkeypatch.setattr(review, 'test_engine', lambda: review.finding('CodeQualityAgent', 'pass', 'stub'))
    monkeypatch.setattr(review, 'AGENTS', (review.test_engine, review.protocol_agent,
                                           review.knowledge_agent, review.benchmark_agent,
                                           review.research_agent, review.submission_agent))
    data = review.run_review(case_count=3)
    assert len(data['agents']) == 6
    assert data['counts']['warning'] >= 1
    assert 'live LLM' not in data['method']
    assert 'not independent generative agents' in data['method']
    assert '| ProtocolSafetyAgent |' in review.markdown_report(data)


def test_failed_checker_makes_automation_fail(monkeypatch):
    monkeypatch.setattr(review, 'AGENTS', (lambda: 1/0,))
    result = review.run_review(case_count=1)
    assert result['status'] == 'failed'
    assert result['counts']['fail'] == 1


def test_supervisor_flags_invalid_report_and_runs_remaining_checks(monkeypatch):
    def invalid():
        return {'agent': 'Tester', 'status': 'passed'}

    def healthy():
        return review.finding('DemoAgent', 'pass', 'demo completed')

    monkeypatch.setattr(review, 'AGENTS', (invalid, healthy))
    result = review.run_review()
    assert result['status'] == 'failed'
    assert result['counts'] == {'pass': 1, 'warning': 0, 'fail': 1}


def test_supervisor_cannot_pass_without_reviewers(monkeypatch):
    monkeypatch.setattr(review, 'AGENTS', ())
    assert review.run_review()['status'] == 'failed'


def test_supervisor_rejects_duplicate_reviewer_identity():
    def reviewer():
        return review.finding('Tester', 'pass', 'suite completed')

    findings = review.ReviewSupervisor((reviewer, reviewer)).run(1)
    assert [item['status'] for item in findings] == ['pass', 'fail']


def test_supervisor_records_callable_failure_and_runs_next_reviewer():
    class OfflineTester:
        def __call__(self):
            raise RuntimeError('private diagnostic')

    def demo():
        return review.finding('DemoAgent', 'pass', 'demo completed')

    findings = review.ReviewSupervisor((OfflineTester(), demo)).run(1)
    assert [item['status'] for item in findings] == ['fail', 'pass']
    assert 'RuntimeError' in findings[0]['detail']
    assert 'private diagnostic' not in findings[0]['detail']
    assert findings[1]['agent'] == 'DemoAgent'


def test_direct_script_help_works_from_outside_project():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, '-E', '-S', str(ROOT / 'scripts' / 'agent_review.py'), '--help'],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert '--cases' in result.stdout


def test_tester_ignores_inherited_pytest_options_and_reports_nonzero(monkeypatch):
    from subprocess import CompletedProcess

    monkeypatch.setenv('PYTEST_ADDOPTS', '--collect-only -k unrelated')

    def run(command, **options):
        assert 'PYTEST_ADDOPTS' not in options['env']
        assert command[-2:] == ['-o', 'addopts=']
        return CompletedProcess(command, 1, stdout='1 failed', stderr='')

    monkeypatch.setattr(review.subprocess, 'run', run)
    result = review.test_engine()
    assert result['status'] == 'fail'
    assert result['evidence']['returncode'] == 1
