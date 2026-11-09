"""Reproducible non-medical acceptance report for structural agent guarantees.
Run: python scripts/acceptance_run.py
All metrics refer to synthetic scenarios and code invariants, not real outcomes.
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from medroute.scenarios import benchmark_scenarios
from medroute.engine import Sandbox
from medroute.council import run_council
from medroute.audit import verify
from medroute.coverage import report as coverage_report

CASES = benchmark_scenarios(30, 2026)
results=[]
for case in CASES:
    game=Sandbox(case)
    before=game.state()
    private=game.advance()
    council=run_council(game)
    disclosed=game.advance()
    supplier=next(x for x in council['trace'] if x['role']=='Supplier')
    results.append({
        'case_id':case['id'],
        'events':disclosed['step'],
        'roles_executed':len(council['trace']),
        'private_capacity_undisclosed_before_formal_event':
            private['scenario']['routes_known'][0]['capacity']!=game.world['routes'][0]['capacity'],
        'private_alert_passed_as_typed_handoff':
            supplier['outgoing_handoff']['intent']=='REQUEST_FORMAL_DISCLOSURE',
        'private_event_blocked_by_operational_check':
            private['release_status']=='BLOCKED_OPERATIONAL',
        'resolved_operationally_after_disclosure':disclosed['operational_check']['passes'],
        'authorization_granted_at_any_step':any(
            'AUTHORIZED'==s['release_status'] for s in (before,private,disclosed)),
        'all_audits_valid':all(s['audit_verification']['valid'] for s in (before,private,disclosed))
                           and council['audit_verification']['valid'],
    })

out={
  'label':'SYNTHETIC structural / protocol acceptance - not clinical, legal, or LLM quality',
  'count':len(results), 'seed':2026,
  'role_runs':sum(x['roles_executed'] for x in results),
  'operational_valid_after_disclosure':sum(x['resolved_operationally_after_disclosure'] for x in results),
  'independent_checker_blocked_stale_plan':sum(x['private_event_blocked_by_operational_check'] for x in results),
  'private_supplier_alert_handoff':sum(x['private_alert_passed_as_typed_handoff'] for x in results),
  'no_autonomous_authorizations':sum(not x['authorization_granted_at_any_step'] for x in results),
  'audit_integrity_valid':sum(x['all_audits_valid'] for x in results),
  'coverage':coverage_report(),
  'cases':results,
  'limitations':[
    'Only synthetic events; not safety validation for real pharmacies.',
    'Offline scripted dialogue is not generative agent performance.',
    'No external pharmacist or UAE qualified legal review performed.',
    'Counterfactual documentation and citations are NOT expert-adjudicated.'
  ]
}
folder=Path('reports');folder.mkdir(exist_ok=True)
(folder/'protocol_acceptance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k in ('count','seed','role_runs','operational_valid_after_disclosure',
  'independent_checker_blocked_stale_plan','private_supplier_alert_handoff',
  'no_autonomous_authorizations','audit_integrity_valid')},indent=2))
