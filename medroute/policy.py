"""Conservative, inspectable policy evidence assessment for a synthetic case.

A missing document in this small proof-of-concept is NOT evidence of a legal gap.
Recommendations are questions for domain/legal experts, not legal permissions.
"""
from .knowledge import claims, catalog
from .disclosure import pending_private_supplier_reports
from .regulatory import transfer_pathway


def policy_matrix(plan, reports, step, product_category='unspecified', emergency_declared=False):
    known_ids = {x['id'] for x in claims()}
    known_sources = {x['id'] for x in catalog()}
    transfer_requested = bool(plan.get('transfers'))
    private_reports = [r for r in reports if 'Coordinator' not in r.get('visible_to', [])]
    # Disclosure can resolve an information gap without proving that a policy is adequate.
    still_private = bool(pending_private_supplier_reports(reports))
    pathway = transfer_pathway(plan.get('transfers', []), product_category, emergency_declared)
    rows = [
        {
            'id': 'P-01',
            'title': 'Product and facility authorization for proposed redistribution',
            'status': 'EVIDENCE_MISSING' if transfer_requested else 'NOT_TRIGGERED',
            'trigger': 'Proposed movement of regulated medical product' if transfer_requested else 'No proposed movement',
            'references': ['C-EDE-002', 'C-EDE-001'] if transfer_requested else [],
            'jurisdiction': 'UAE',
            'missing': ['full applicable legal text', 'product-specific regulatory status',
                        'facility credentials', 'written authorization / sign-off'],
            'question': 'Who may approve an inter-facility movement of this exact product, and what are the prerequisites?',
            'proposed_research': 'Obtain binding UAE regulations and confirmation from qualified pharmaceutical counsel.',
            'is_confirmed_legal_gap': False,
        },
        {
            'id': 'P-02',
            'title': 'Inter-institutional escalation and information-sharing protocol',
            'status': ('REVIEW_REQUIRED' if still_private else
                       'DISCLOSED_FOR_REVIEW' if private_reports else 'NOT_TRIGGERED'),
            'trigger': ('Material update remains unavailable to Coordinator' if still_private else
                        'Earlier private update was subsequently disclosed' if private_reports else 'No private update observed'),
            'references': ['C-ITU-002', 'C-EDE-001'] if private_reports else [],
            'jurisdiction': 'UAE / cross-institutional',
            'missing': ['relevant data-sharing protocol', 'responsible escalation authority',
                        'formal disclosure timing and audit controls'],
            'question': 'What are the permitted channels and escalation duties for supply alerts shared between institutions?',
            'proposed_research': 'Compare documented escalation mandates across agencies and suppliers.',
            'is_confirmed_legal_gap': False,
        },
        {
            'id': 'P-04',
            'title': 'Data minimization, confidentiality and accountable AI sharing',
            'status': 'APPLICABILITY_REVIEW_REQUIRED' if private_reports else 'MONITOR',
            'trigger': 'Cross-organization supplier disclosure and AI assessment',
            'references': ['C-UAIPDPL-001', 'C-UAE-HEALTHICT-001', 'C-UAE-HEALTHICT-002',
                           'C-UAICHARTER-001', 'C-UAICYBER-001'],
            'jurisdiction': 'UAE',
            'missing': ['full applicable privacy rules and exemptions',
                        'appropriate institution-level data-sharing agreement',
                        'AI security policy applicability and governance approvals'],
            'question': 'Which data may each actor disclose, to whom, and under what verified basis?',
            'proposed_research': 'Verify with current UAE binding data law, healthcare mandates and legal/privacy reviewers.',
            'is_confirmed_legal_gap': False,
        },
        {
            'id': 'P-03',
            'title': 'Transferability of international shortage coordination practices',
            'status': 'COMPARATOR_ONLY',
            'trigger': 'Optional global best-practice comparison',
            'references': ['C-EMA-001'],
            'jurisdiction': 'EU/EEA example; NOT UAE law',
            'missing': ['local applicability assessment', 'identified jurisdictional differences'],
            'question': 'Which coordination features in the EMA solidarity mechanism are reusable as design patterns?',
            'proposed_research': 'Map roles, data exchange, escalation and legal authority without transplanting EU law.',
            'is_confirmed_legal_gap': False,
        },
        {
            'id': 'P-05',
            'title': 'Emergency controlled-medicine approval workflow (scope-specific)',
            'status': ('REVIEW_REQUIRED' if pathway['status'] ==
                       'EDE_EMERGENCY_TRANSFER_REVIEW_REQUIRED' else 'NOT_TRIGGERED'),
            'trigger': ('Explicit synthetic controlled/psychotropic category AND declared emergency with proposed transfer'
                        if pathway['status'] == 'EDE_EMERGENCY_TRANSFER_REVIEW_REQUIRED'
                        else 'No in-scope emergency controlled-medicine proposal'),
            'references': pathway['source_claim_ids'] if pathway['status'] ==
                          'EDE_EMERGENCY_TRANSFER_REVIEW_REQUIRED' else [],
            'jurisdiction': 'UAE',
            'missing': pathway['review_documents'] if pathway['status'] ==
                       'EDE_EMERGENCY_TRANSFER_REVIEW_REQUIRED' else [],
            'question': 'Does the official EDE emergency service apply to this exact product and facility, and has an authorized official approved it?',
            'proposed_research': 'Check the EDE service requirements with a qualified authority; do not collect patient records in this simulator.',
            'is_confirmed_legal_gap': False,
        },
    ]
    for row in rows:
        if any(ref not in known_ids for ref in row['references']):
            raise ValueError(f'Uncatalogued evidence in policy row {row["id"]}')
    return {'scope': 'research hypotheses only; not a determination that the law is missing',
            'case_step': step, 'rows': rows,
            'confirmed_legal_gaps': 0,
            'questions_requiring_expert_review': sum(r['status'] in ('EVIDENCE_MISSING','REVIEW_REQUIRED','APPLICABILITY_REVIEW_REQUIRED') for r in rows),
            'source_catalogue_size': len(known_sources)}


def evidence_dossier(state):
    """Export only inspectable information; never label unverified summaries 'statute'."""
    source_ids = {s['id'] for s in catalog()}
    citations = {c['id']: c for c in claims()}
    refs = sorted(set(
        ref for agent in state['agents'] for ref in agent.get('references', [])
    ).union(ref for row in state['policy_matrix']['rows'] for ref in row['references'])
    .union(state['legal_check'].get('evidence', [])))
    for claim_id in refs:
        if claim_id not in citations or citations[claim_id]['source_id'] not in source_ids:
            raise ValueError('Evidence export failed: unknown citation')
    return {
        'title': 'MedRoute X - reviewable simulation evidence dossier',
        'status': state['release_status'],
        'simulation_only': True, 'automated_approval_granted': False,
        'scenario': state['scenario'],
        'step': state['step'], 'proposed_plan': state['plan'],
        'operational_test': state['operational_check'],
        'legal_review': state['legal_check'],
        'policy_matrix': state['policy_matrix'],
        'agent_assessments': state['agents'],
        'claim_references': [dict(citations[ref],
                                   source=next(s for s in catalog() if s['id']==citations[ref]['source_id']))
                             for ref in refs],
        'audit': state['audit'], 'audit_verification': state['audit_verification'],
        'limitations': [
            'Synthetic inventory, demand, routes, and urgency weights',
            'No patient records or clinical triage',
            'No product-specific legal determination or authority to transfer',
            'Role outputs are deterministic; optional LLM integration is separate and untested live',
            'The knowledge base contains verified source-level summaries, not the full corpus of UAE legal texts'
        ],
    }
