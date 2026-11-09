"""Reproducible sprint-3 HTTP boundary acceptance; no external network or LLM calls.

Run from the project root: PYTHONPATH=. python scripts/sprint3_acceptance.py
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                          timeout=120, check=False)
    output = proc.stdout + '\n' + proc.stderr
    matched = re.search(r'(\d+) passed', output)
    return {'command': command, 'exit_code': proc.returncode,
            'passed_count': int(matched.group(1)) if matched else None,
            'output_tail': output[-1800:]}


def main():
    boundary = run([sys.executable, '-m', 'pytest', '-q', 'tests/test_sprint3_http_boundary.py'])
    all_tests = run([sys.executable, '-m', 'pytest', '-q'])
    node = shutil.which('node')
    js = run([node, '--check', 'web/app.js']) if node else {
        'status': 'NOT_RUN_NODE_NOT_INSTALLED', 'exit_code': None}
    success = (boundary['exit_code'] == 0 and boundary['passed_count'] == 18
               and all_tests['exit_code'] == 0 and js['exit_code'] in (0, None))
    result = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'project_version': '0.7.0',
        'status': 'pass' if success else 'fail',
        'scope': 'loopback HTTP hardening and offline synthetic regression only',
        'security_regression': boundary,
        'full_pytest': all_tests,
        'javascript_syntax': js,
        'provenance': 'tests run against unpacked v0.6-derived project; no external network',
        'limitations': [
            'Not user authentication; local processes can still access the simulator.',
            'Not penetration testing or a production deployment security assessment.',
            'No live LLM test or real patient/institutional data.',
            'No binding UAE law text or expert legal review verified.',
            'No GitHub publication or ITU submission.'
        ]
    }
    target = ROOT / 'reports' / 'sprint3_acceptance.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'],
                      'security_tests_passed': boundary['passed_count'],
                      'full_tests_passed': all_tests['passed_count'],
                      'javascript_exit_code': js['exit_code'],
                      'report': str(target)}, ensure_ascii=False))
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
