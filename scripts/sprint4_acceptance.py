"""Offline reproducible sprint-4 acceptance; no API, no real patient records."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from medroute.audit import verify
from medroute.council import run_council, verify_council_artifact
from medroute.coverage import report as coverage_report
from medroute.engine import Sandbox
from medroute.policy import evidence_dossier
from medroute.retrieval_eval import evaluate_retrieval
from medroute.scenarios import controlled_emergency


def main():
    tests = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=ROOT,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=180, check=False)
    match = re.search(r'(\d+) passed', tests.stdout)
    passed = int(match.group(1)) if match else 0
    game = Sandbox(controlled_emergency())
    snapshots = [game.state(), game.advance(), game.advance()]
    council = run_council(game, roles=['Regulator', 'Coordinator', 'Auditor'])
    dossier = evidence_dossier(game.state())
    source_ids = {x['id'] for x in dossier['claim_references']}
    checks = {
        'all_tests_passed': tests.returncode == 0,
        'three_states_no_authorization': all(
            s['legal_check']['status'] == 'HUMAN_REVIEW_REQUIRED' and
            s['legal_check']['regulatory_pathway']['authorization_granted'] is False and
            s['release_status'] != 'AUTHORIZED' for s in snapshots),
        'controlled_service_only_under_explicit_emergency': all(
            s['legal_check']['regulatory_pathway']['status'] ==
            'EDE_EMERGENCY_TRANSFER_REVIEW_REQUIRED' for s in snapshots),
        'policy_evidence_traced': {'C-EDE-EMERG-001', 'C-EDE-EMERG-002'} <= source_ids,
        'all_three_audits_valid': all(verify(s['audit'])['valid'] for s in snapshots),
        'council_artifact_valid': verify_council_artifact(council)['valid'],
        'no_agent_authorizations': all(not x['transfer_authorized'] for x in council['trace']),
        'no_patient_data_collected': all(not s['legal_check']['regulatory_pathway']['accepts_patient_data']
                                         for s in snapshots),
    }
    output = {
        'sprint': 4, 'release': 'v0.8.0', 'date': '2026-10-30',
        'method': 'offline Python tests and deterministic simulation; no live LLM, no legal clearance',
        'baseline_tests_passed': 100, 'current_tests_passed': passed,
        'pytest_returncode': tests.returncode,
        'pytest_tail': tests.stdout[-700:],
        'checks': checks,
        'retrieval_original_eight': evaluate_retrieval(),
        'retrieval_new_two': evaluate_retrieval(ROOT / 'benchmarks/policy_retrieval_sprint4_gold.json'),
        'kb': {'source_count': coverage_report()['source_count'],
               'claim_count': coverage_report()['claim_count']},
        'scenario_statuses': [s['release_status'] for s in snapshots],
        'official_sources_reviewed': [
            'https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/',
            'https://ede.gov.ae/en/w/approve-emergency-drugs-and-psychotropic-materials',
            'https://uaelegislation.gov.ae/en/legislations/2751',
        ],
        'limitations': [
            'No official agency approval or professional legal opinion.',
            'EDE emergency service only applies to its narrow published scope.',
            'The synthetic category/emergency flags are not verified real-world classification.',
            'No patient information, live LLM calls, or GitHub writes.',
            'Retrieval results are tiny manually authored QA cases, not legal accuracy.',
        ],
    }
    target = ROOT / 'reports/sprint4_acceptance.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': passed, 'all_checks': all(checks.values()),
                      'checks': checks, 'artifact': str(target)}, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
