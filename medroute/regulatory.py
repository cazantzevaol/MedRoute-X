"""Narrow, evidence-linked regulatory triage for *synthetic* proposals.

A product category is an explicit scenario assumption, never inferred from a name
or asserted by an LLM. This module cannot grant approval or collect patient data.
"""

VALID_PRODUCT_CATEGORIES = frozenset({
    'unspecified', 'general_medical_product', 'controlled_or_psychotropic'
})


def transfer_pathway(transfers, product_category='unspecified', emergency_declared=False):
    """Identify a *review pathway*, not permission to distribute a medicine.

    EDE's emergency transfer service has a narrow scope. In particular, do NOT
    apply it to every inter-facility movement or treat its existence as approval.
    """
    if type(emergency_declared) is not bool:
        raise ValueError('emergency_declared must be an explicit boolean scenario assumption')
    if product_category not in VALID_PRODUCT_CATEGORIES:
        raise ValueError('Unknown scenario product category; do not infer regulatory class')
    common = {
        'product_category': product_category,
        'emergency_declared': emergency_declared,
        'classification_verified': False,
        'authorization_granted': False,
        'accepts_patient_data': False,
        'human_authority_required': True,
    }
    if not transfers:
        return {**common, 'status': 'NOT_TRIGGERED', 'source_claim_ids': [],
                'scope': 'No transfer proposed', 'review_documents': []}
    if product_category == 'controlled_or_psychotropic' and emergency_declared:
        return {**common, 'status': 'EDE_EMERGENCY_TRANSFER_REVIEW_REQUIRED',
                'source_claim_ids': ['C-EDE-EMERG-001', 'C-EDE-EMERG-002'],
                'scope': ('Official EDE service for emergency transfer of narcotic, '
                          'psychotropic and semi-controlled medicines between eligible facilities; '
                          'not a blanket inter-hospital permit'),
                'review_documents': [
                    'Facility director justification letter specifying quantities',
                    'Current facility and responsible doctor/pharmacist licences',
                    'NOC from the competent licensing authority',
                    'Import permit of the transferring health facility',
                    'Patient-related supporting records, if applicable: ONLY via the '
                    'official authorized EDE channel, NEVER through MedRoute X',
                ],
                'next_step': 'Qualified UAE regulatory officer must verify classification, '
                             'eligibility, required records and official approval.'}
    return {**common, 'status': ('CONTROLLED_PRODUCT_REVIEW_REQUIRED' if
                                product_category == 'controlled_or_psychotropic' else
                                'PRODUCT_SPECIFIC_REVIEW_REQUIRED'),
            'source_claim_ids': ['C-UAEFDL38-001'],
            'scope': ('General product rules and institution-specific authority require '
                      'independent review; EDE emergency controlled-medicine service '
                      'is NOT automatically applicable'),
            'review_documents': ['Verified product classification and authorization',
                                 'Facility-specific permissions and applicable distribution rules'],
            'next_step': 'Request qualified UAE product-specific legal and pharmacy review.'}
