"""Regression: top-level safety metadata must be bound to exported artifact."""
from copy import deepcopy
import pytest
from medroute.council import run_council, verify_council_artifact
from medroute.engine import Sandbox

@pytest.fixture
def artifact():
    result = run_council(Sandbox(), roles=['Regulator'])
    assert verify_council_artifact(result)['valid']
    return result

@pytest.mark.parametrize('field,value', [
    ('human_approval_required', False),
    ('release_status_from_independent_engine', 'APPROVED'),
    ('scenario_id', 'swapped-scenario'),
    ('no_execution_or_medical_advice', False),
    ('limitations', []),
])
def test_tampered_top_level_rejected(artifact, field, value):
    tampered = deepcopy(artifact)
    tampered[field] = value
    assert verify_council_artifact(tampered) == {
        'valid': False, 'reason': 'artifact_envelope_modified'}

def test_missing_digest_rejected(artifact):
    del artifact['artifact_sha256']
    assert verify_council_artifact(artifact)['valid'] is False

def test_digest_is_reproducible(artifact):
    from hashlib import sha256
    from medroute.council import canonical
    payload = {k: v for k, v in artifact.items()
               if k not in ('artifact_sha256', 'artifact_verification')}
    assert sha256(canonical(payload).encode()).hexdigest() == artifact['artifact_sha256']
