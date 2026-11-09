import copy
import pytest
from medroute.knowledge import catalog, claims, search_claims, validate_evidence_integrity


def test_real_catalog_has_unique_traceable_ids():
    result = validate_evidence_integrity(catalog(), claims())
    assert result['integrity'] == 'PASS'
    assert result['legal_review'] == 'NOT_PERFORMED'


def test_duplicate_source_is_rejected():
    sources = catalog()
    with pytest.raises(ValueError, match='duplicate'):
        validate_evidence_integrity(sources + [copy.deepcopy(sources[0])], claims())


def test_duplicate_claim_is_rejected():
    items = claims()
    with pytest.raises(ValueError, match='duplicate'):
        validate_evidence_integrity(catalog(), items + [copy.deepcopy(items[0])])


def test_dangling_claim_reference_is_rejected():
    items = copy.deepcopy(claims())
    items[0]['source_id'] = 'MISSING-SOURCE'
    with pytest.raises(ValueError, match='missing source'):
        validate_evidence_integrity(catalog(), items)


@pytest.mark.parametrize('url', ['http://ede.gov.ae/example', 'https://user:secret@ede.gov.ae/path',
                                 'https://ede.gov.ae/a#fragment', 'javascript:alert(1)',
                                 'https://ede.gov.ae/a b'])
def test_unsafe_source_urls_are_rejected(url):
    sources = copy.deepcopy(catalog())
    sources[0]['url'] = url
    with pytest.raises(ValueError, match='URL'):
        validate_evidence_integrity(sources, claims())


def test_search_fails_closed_on_ambiguous_sources(monkeypatch):
    import medroute.knowledge as knowledge
    sources = catalog()
    monkeypatch.setattr(knowledge, 'catalog', lambda: sources + [copy.deepcopy(sources[0])])
    with pytest.raises(ValueError, match='duplicate'):
        search_claims('UAE medicine')
