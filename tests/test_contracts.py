from copy import deepcopy
import pytest
from contracts import candidate_export, validate_candidate_export
from listings import ValidationError
from scanner import ListingStore
from imports import parse_import
from test_imports import raw_listing, encode, NOW


def test_manual_selection_export_bound_to_snapshot(tmp_path):
    store = ListingStore(tmp_path / 'db.sqlite3')
    raw = raw_listing()
    store.ingest(parse_import(encode(raw), 'json', NOW), 'internal', 'a')
    assert candidate_export(store, 'internal')['candidates'] == []
    store.set_decision('internal', *('test-source', 'test-1'), 'candidate')
    exported = candidate_export(store, 'internal')
    assert len(validate_candidate_export(exported, NOW)['candidates']) == 1
    assert candidate_export(store, 'other')['candidates'] == []
    raw['observed_at'] = '2026-10-10T12:00:00Z'
    store.ingest(parse_import(encode(raw), 'json', NOW), 'internal', 'b')
    assert candidate_export(store, 'internal')['candidates'] == []


def test_candidate_contract_rejects_identity_or_snapshot_conflicts(tmp_path):
    store = ListingStore(tmp_path / 'db.sqlite3')
    store.ingest(parse_import(encode(raw_listing()), 'json', NOW), 'internal', 'a')
    store.set_decision('internal', 'test-source', 'test-1', 'candidate')
    exported = candidate_export(store, 'internal')
    for field, value in [('offer_key', ['wrong', 'id']), ('approved_snapshot_at', '2026-10-10T12:00:00Z'), ('approval_status', 'purchased')]:
        invalid = deepcopy(exported)
        invalid['candidates'][0][field] = value
        with pytest.raises(ValidationError):
            validate_candidate_export(invalid, NOW)
    exported['candidates'] *= 2
    with pytest.raises(ValidationError):
        validate_candidate_export(exported, NOW)
