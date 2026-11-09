"""Deterministic offline quality-agent pipeline for MedRoute X.

These are autonomous *checks*, not independent LLMs and not healthcare or legal
reviewers. No network calls, no external API keys, no edits to source code.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__' and not __package__:
    sys.path.insert(0, str(ROOT))

from medroute.council import run_council, verify_council_artifact
from medroute.coverage import report as coverage_report
from medroute.engine import Sandbox
from medroute.scenarios import multi_alert_disclosure
from medroute.evaluate import evaluate
from medroute.retrieval_eval import evaluate_retrieval

def finding(name: str, status: str, detail: str, evidence: dict | None = None) -> dict:
    if status not in ('pass', 'warning', 'fail'):
        raise ValueError('Unsupported status')
    return {'agent': name, 'status': status, 'detail': detail, 'evidence': evidence or {}}


def test_engine() -> dict:
    """Runs pytest as subprocess so a CI failure cannot masquerade as a pass."""
    command = [sys.executable, '-m', 'pytest', '-q', '-o', 'addopts=']
    env = os.environ.copy()
    env.pop('PYTEST_ADDOPTS', None)
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                            timeout=120, check=False)
    tail = (result.stdout + '\n' + result.stderr)[-2200:]
    return finding('CodeQualityAgent', 'pass' if result.returncode == 0 else 'fail',
                   'Unit and regression tests executed with pytest.',
                   {'returncode': result.returncode, 'command': command[1:], 'output_tail': tail})


def protocol_agent() -> dict:
    """Cross-check role count, ledger verification and independent gates for all states."""
    game = Sandbox()
    seen = []
    problems = []
    for step in range(3):
        if step:
            game.advance()
        state = game.state()
        council = run_council(game)
        verified = verify_council_artifact(council)
        legal_safe = all(t['transfer_authorized'] is False and t['review_required'] is True
                         for t in council['trace'])
        role_count = len(council['trace'])
        ok = verified['valid'] and role_count == 10 and legal_safe
        if not ok:
            problems.append({'step': step, 'verified': verified, 'roles': role_count,
                             'authorization_safe': legal_safe})
        seen.append({'step': step, 'roles': role_count, 'audit_valid': verified['valid'],
                     'no_agent_authorizations': legal_safe,
                     'operational_pass': state['operational_check']['passes'],
                     'release_status': state['release_status']})
    # Sprint-2: an earlier disclosure must never silence a later private alert.
    second = Sandbox(multi_alert_disclosure())
    alert_pattern = []
    public_redaction_ok = True
    for step in range(5):
        if step:
            second.advance()
        public = second.state()
        council = run_council(second, roles=['Supplier', 'Coordinator', 'Auditor'])
        supplier = next(x for x in council['trace'] if x['role'] == 'Supplier')
        alert_pattern.append(supplier['outgoing_handoff']['intent'] == 'REQUEST_FORMAL_DISCLOSURE')
        if not council['artifact_verification']['valid'] or not public['audit_verification']['valid']:
            problems.append({'scenario': 'CASE-002', 'step': step, 'issue': 'audit_invalid'})
        serialized = json.dumps(public, ensure_ascii=False)
        for internal in second.reports:
            if 'Coordinator' not in internal['visible_to'] and internal['message'] in serialized:
                public_redaction_ok = False
    expected = [False, True, False, True, False]
    if alert_pattern != expected or not public_redaction_ok:
        problems.append({'scenario': 'CASE-002', 'issue': 'disclosure_boundary_failed'})
    return finding('ProtocolSafetyAgent', 'fail' if problems else 'pass',
                   'Three flagship states plus five per-alert disclosure states assessed.',
                   {'states': seen, 'disclosure_alert_pattern': alert_pattern,
                    'public_redaction_ok': public_redaction_ok,
                    'problems': problems, 'mode': 'offline_scripted'})


def knowledge_agent() -> dict:
    kb = coverage_report()
    retrieval = evaluate_retrieval()
    orphan = kb['orphan_claim_sources']
    missing = kb['missing_curated_sources']
    malformed = bool(orphan or missing)
    status = 'fail' if malformed else 'warning'
    return finding('KnowledgeEvidenceAgent', status,
                   'Full binding UAE texts and expert validation are still missing.' if not malformed
                   else 'Unresolved source references found.',
                   {'source_count': kb['source_count'], 'claim_count': kb['claim_count'],
                    'orphan_sources': orphan, 'missing_sources': missing,
                    'national_full_text_complete': False,
                    'expert_review_complete': False,
                    'curated_retrieval': {k: v for k, v in retrieval.items() if k != 'cases'},
                    'retrieval_note': 'Near-source curated queries; not proof of legal retrieval accuracy.'})


def benchmark_agent(count: int) -> dict:
    bench = evaluate(count=count, seed=2026)
    stats = bench['stats']
    valid = all(row['operational_valid'] is True and
                row['legal_approval'] == 'not_granted_by_demo' for row in bench['records'])
    bounded = all(stats[m]['scenarios'] == count for m in ('greedy', 'optimized', 'local_only'))
    weighted_delta = bench['priority_weighted_reduction_vs_greedy_percent']
    return finding('ExperimentAgent', 'pass' if valid and bounded else 'fail',
                   'Seeded synthetic baseline comparison; improvements are not clinical outcomes.',
                   {'case_count': count, 'seed': bench['seed'],
                    'priority_weighted_reduction_percent': weighted_delta,
                    'greedy_unmet': stats['greedy']['mean_unmet_units'],
                    'optimized_unmet': stats['optimized']['mean_unmet_units'],
                    'operational_valid_all': valid, 'per_method_count_correct': bounded})


def research_agent() -> dict:
    novelty = ROOT / 'reports' / 'SCIENTIFIC_NOVELTY_SPRINT1.md'
    rules = ROOT / 'reports' / 'ITU_RULES_ALIGNMENT_SPRINT1.md'
    expected = {'novelty_scan': novelty.exists(), 'itu_traceability': rules.exists()}
    status = 'warning' if all(expected.values()) else 'fail'
    return finding('ResearchAndITUAgent', status,
                   'Existing desk research needs independent freshness and novelty verification; '
                   'published contest criteria are mapped but not formally scored.' if status == 'warning'
                   else 'Required research or ITU traceability file is absent.',
                   {**expected, 'live_web_research_performed': False,
                    'validated_world_first_novelty': False, 'official_jury_score': None})


def submission_agent() -> dict:
    names = {
        'report_pdf': ROOT / 'reports' / 'technical_report.pdf',
        'demo_script': ROOT / 'reports' / 'demo_script_en.md',
        'knowledge_sources': ROOT / 'kb' / 'sources.json',
        'submission_readiness': ROOT / 'reports' / 'submission_readiness.md',
    }
    exists = {key: val.is_file() and val.stat().st_size > 0 for key, val in names.items()}
    status = 'warning' if all(exists.values()) else 'fail'
    return finding('SubmissionAgent', status,
                   'Local deliverables present; GitHub publishing, expert review, actual live LLM tests '
                   'and competition submission remain outside this automation.' if status == 'warning'
                   else 'Some locally required documents are missing.',
                   {'artifacts': exists, 'github_published': False,
                    'submitted_to_itu': False, 'live_llm_validated': False,
                    'pdf_page_limit_verified_by_this_agent': False})


AGENTS: tuple[Callable[..., dict], ...] = (test_engine, protocol_agent, knowledge_agent,
                                           benchmark_agent, research_agent, submission_agent)


class ReviewSupervisor:
    """Coordinate the local reviewers and reject invalid or failed reports."""

    def __init__(self, checks):
        self.checks = tuple(checks)

    def run(self, case_count):
        if not self.checks:
            return [finding('ReviewSupervisor', 'fail', 'No reviewers configured.')]
        findings = []
        for checker in self.checks:
            try:
                result = checker(case_count) if checker is benchmark_agent else checker()
                if (not isinstance(result, dict)
                        or result.get('status') not in ('pass', 'warning', 'fail')
                        or not isinstance(result.get('agent'), str)
                        or not result['agent'].strip()
                        or not isinstance(result.get('detail'), str)
                        or not isinstance(result.get('evidence'), dict)):
                    raise ValueError('Invalid reviewer report')
                if any(item['agent'] == result['agent'] for item in findings):
                    raise ValueError('Duplicate reviewer identity')
                json.dumps(result, allow_nan=False)
            except (Exception, SystemExit) as exc:
                name = getattr(checker, '__name__', type(checker).__name__)
                result = finding(name, 'fail',
                                 f'Automated check raised {type(exc).__name__}; inspect locally.')
            findings.append(result)
        return findings


def run_review(case_count: int = 30) -> dict:
    """Run the offline review under supervision."""
    agents = ReviewSupervisor(AGENTS).run(case_count)
    counts = {level: sum(x['status'] == level for x in agents)
              for level in ('pass', 'warning', 'fail')}
    return {'name': 'MedRoute X automated reviewer council',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'method': 'offline deterministic checks, not independent generative agents',
            'case_count': case_count, 'status': 'failed' if counts['fail'] else 'completed_with_warnings'
            if counts['warning'] else 'passed', 'counts': counts, 'agents': agents,
            'non_claims': ['No verified clinical, legal or public-sector expert approval.',
                           'No GitHub access, no external LLM API usage, no deployment.',
                           'No claim that medicine transfers are permitted.']}


def markdown_report(report: dict) -> str:
    lines = ['# MedRoute X — Automated Agent Review', '',
             f"Generated (UTC): {report['generated_at_utc']}",
             f"Status: **{report['status']}**. Checks: {report['counts']}", '',
             'This is a deterministic, offline quality-assurance team, **not** a live LLM swarm.',
             '', '| Agent | Status | Finding |', '|---|---|---|']
    for item in report['agents']:
        lines.append(f"| {item['agent']} | {item['status'].upper()} | {item['detail'].replace('|', '/')} |")
    lines += ['', '## Priority gaps (not hidden)',
              '1. Import and review full, current UAE pharmaceutical legal text with section-level citations.',
              '2. Run a separately authorized live LLM agent test with synthetic data and costs bounded.',
              '3. Expert-review healthcare and legal applicability claims, and verify comparative research.',
              '4. Publish a licensed repository and submit the 5-page report and KB before the deadline.',
              '', 'Generated checks never approve medicine movements or real-world treatments.']
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', default='reports/agent_automation')
    parser.add_argument('--cases', type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.cases <= 500:
        parser.error('--cases must be between 1 and 500')
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)
    payload = run_review(case_count=args.cases)
    # Persist bounded JSON, no API keys or real patient data are accessed.
    (outdir / 'agent_review.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    (outdir / 'agent_review.md').write_text(markdown_report(payload), encoding='utf-8')
    print(json.dumps({'status': payload['status'], 'counts': payload['counts'],
                      'artifacts': [str(outdir / 'agent_review.json'),
                                    str(outdir / 'agent_review.md')]}, ensure_ascii=False))
    return 1 if payload['counts']['fail'] else 0


if __name__ == '__main__':
    sys.exit(main())
