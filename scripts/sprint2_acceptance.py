"""Re-run offline sprint-2 checks and write a truthful machine-readable result.

No LLM calls, GitHub writes, patient data, or medical approvals.
Run from the project root: PYTHONPATH=. python scripts/sprint2_acceptance.py
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

from medroute.engine import Sandbox
from medroute.council import run_council
from medroute.coverage import report as coverage_report
from medroute.scenarios import multi_alert_disclosure

ROOT = Path(__file__).resolve().parents[1]


def run_command(command):
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                          timeout=120, check=False)
    return {'command': command, 'exit_code': proc.returncode,
            'output_tail': (proc.stdout + '\n' + proc.stderr)[-1200:]}


def main():
    tests = run_command([sys.executable, '-m', 'pytest', '-q'])
    node = shutil.which('node')
    js = run_command([node, '--check', 'web/app.js']) if node else {
        'status': 'NOT_RUN_NODE_NOT_INSTALLED', 'exit_code': None}
    game = Sandbox(multi_alert_disclosure())
    stages = []
    for step in range(5):
        if step:
            game.advance()
        state = game.state()
        council = run_council(game, roles=['Supplier', 'Coordinator', 'Auditor'])
        supplier = next(t for t in council['trace'] if t['role'] == 'Supplier')
        stages.append({'step': step,
                       'alert': supplier['outgoing_handoff']['intent'] == 'REQUEST_FORMAL_DISCLOSURE',
                       'operational_pass': state['operational_check']['passes'],
                       'audit_valid': state['audit_verification']['valid'] and council['artifact_verification']['valid'],
                       'legal_status': state['legal_check']['status']})
    expected = [False, True, False, True, False]
    status = ('pass' if tests['exit_code'] == 0 and js['exit_code'] in (0, None)
              and [s['alert'] for s in stages] == expected
              and all(s['audit_valid'] and s['legal_status'] == 'HUMAN_REVIEW_REQUIRED' for s in stages)
              else 'fail')
    result = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': status, 'scope': 'offline synthetic regression only',
              'pytest': tests, 'javascript': js,
              'disclosure_scenario': {'id': 'CASE-002', 'stages': stages},
              'knowledge': {'source_pointers': coverage_report()['source_count'],
                            'summary_claims': coverage_report()['claim_count'],
                            'binding_full_text_verified': False},
              'limitations': ['No live LLM test', 'No legal or clinical expert signoff',
                              'No GitHub publication or competition submission']}
    path = ROOT / 'reports' / 'sprint2_acceptance.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': status, 'report': str(path),
                      'pytest_exit_code': tests['exit_code'],
                      'javascript_exit_code': js['exit_code'],
                      'disclosure_alert_pattern': [s['alert'] for s in stages]}, ensure_ascii=False))
    return 0 if status == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
