"""Fabricated offers only."""
from dataclasses import replace
from test_imports import raw_listing, NOW
from listings import Listing
from intelligence import analyze_listing, possible_duplicates, filter_listings


def lot(): return Listing.parse(raw_listing(), NOW)


def test_evidence_and_original_unchanged():
    original = replace(lot(), title='4 Stück Vitra Bürostuhl')
    before = original.to_dict()
    result = analyze_listing(original, 'gebraucht, Metall, Kratzer')
    assert result['quantity']['value'] == 4
    assert result['brand']['value'] == ['vitra']
    assert result['category']['value'] == ['seating']
    text = original.title + '\ngebraucht, Metall, Kratzer'
    for evidence in result['damage']['evidence']:
        assert text[evidence['start']:evidence['end']] == evidence['text']
    assert original.to_dict() == before


def test_ambiguous_count_and_unknown_model():
    result = analyze_listing(replace(lot(), title='2 Stück Stühle, 3 Stück Tische'))
    assert result['quantity']['origin'] == 'unknown'
    assert result['model']['value'] is None
    assert analyze_listing(replace(lot(), title='Metallisch unverifiziert'))['material']['value'] is None


def test_candidates_are_not_deleted():
    a = lot(); b = replace(a, source='another'); c = replace(a, source_id='other')
    result = possible_duplicates([a, b, c])
    assert len(result) == 2 and all(d['status'] == 'possible' for d in result)


def test_filters():
    a = replace(lot(), title='Vitra Stuhl'); b = replace(a, source='another', status='ended')
    assert filter_listings([a, b], {'source': a.source, 'category': 'seating', 'min_price': 1000, 'max_price': 1000, 'upcoming': True}, NOW) == [a]
    assert filter_listings([a], {'max_price': 999}, NOW) == []
    assert filter_listings([a], {'ends_before': '2026-10-10T12:00:00Z'}, NOW) == []
