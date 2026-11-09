"""Inspectable, conservative country knowledge coverage report.

Coverage means that public source pointers exist. It does NOT prove completeness,
semantic citation support, current law, or legal review of underlying texts.
"""
import json
from collections import Counter
from .knowledge import catalog, claims

CATEGORIES = {
    'medical_product_law': ('EDE-LAW', 'UAE-FDL38-2024'),
    'emergency_controlled_transfer_service': ('EDE-EMERGENCY-TRANSFER',),
    'pharmaceutical_supply_policy': ('EDE-MULTI-AGENT',),
    'national_ai_governance': ('UAE-AI-CHARTER', 'UAE-AI-INTL'),
    'national_ai_security': ('UAE-AI-CYBER',),
    'personal_data_protection': ('UAE-PDPL-INDEX',),
    'health_information_confidentiality': ('UAE-HEALTHICT-2019',),
    'international_essential_medicines': ('WHO-EML-2025',),
    'international_shortage_response': ('EMA-VSM',),
    'itu_rules_and_standard': ('ITU-CHALLENGE', 'ITU-Y3172'),
}

def report():
    sources = {s['id']: s for s in catalog()}
    statements = claims()
    missing = sorted({sid for values in CATEGORIES.values() for sid in values if sid not in sources})
    dangling = sorted({c['source_id'] for c in statements if c['source_id'] not in sources})
    return {
        'source_count': len(sources), 'claim_count': len(statements),
        'category_coverage': {name: {
            'source_ids':[sid for sid in source_ids if sid in sources],
            'linked_claim_count': sum(c['source_id'] in source_ids for c in statements),
            'full_binding_text_ingested': False, 'expert_review_complete': False,
        } for name, source_ids in CATEGORIES.items()},
        'missing_curated_sources': missing, 'orphan_claim_sources': dangling,
        'jurisdictions': dict(Counter(s['jurisdiction'] for s in sources.values())),
        'known_gaps': [
            'Full currently operative binding pharmaceutical provisions not independently reviewed',
            'Product-specific and institution-specific authorization not established',
            'Data-sharing applicability and exceptions not independently reviewed',
            'UAE Health ICT Law 2/2019 Articles 4/13/16 checked in English; Arabic and applicability pending',
            'Claim entailment requires human annotation; source existence is not proof',
        ],
        'status':'metadata_and_page_summary_only_not_full_national_kb',
    }

if __name__ == '__main__':
    print(json.dumps(report(), ensure_ascii=False, indent=2))
