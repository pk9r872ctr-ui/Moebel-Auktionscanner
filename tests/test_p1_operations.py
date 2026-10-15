"""All listings, identities and passwords here are synthetic test data."""
from pathlib import Path
from dataclasses import replace
import json
import shutil
import sqlite3
import pytest
from streamlit.testing.v1 import AppTest
from backup_transport import encrypted_backup,restore_encrypted,HEADER
from scanner import ListingStore
from imports import parse_import
from test_imports import raw_listing,encode,NOW
from test_p0_import import payload as p0_payload
from research_import import parse_p0_csv
from contracts import candidate_export,validate_candidate_export
from assessment import assess_listing
from scoring import Assumptions
from extended_economics import risk_adjusted_assumptions
from listings import ValidationError


def prepared(tmp_path):
    store=ListingStore(tmp_path/'db.sqlite3')
    store.ingest(parse_import(encode(raw_listing()),'json',NOW),'internal','synthetic-regular')
    store.set_decision('internal','test-source','test-1','watchlist','Synthetic decision')
    store.ingest(parse_p0_csv(p0_payload(2),now=NOW),'internal','synthetic-p0')
    store.record_scan('internal',[{'file':'synthetic.csv','status':'ok'}])
    return store


def test_encrypted_end_to_end_restore_keeps_everything_and_renders(tmp_path,monkeypatch):
    store=prepared(tmp_path)
    cipher=encrypted_backup(store,'SYNTHETIC-password-only-123')
    assert cipher.startswith(HEADER) and b'SQLite format' not in cipher
    restored_path=restore_encrypted(cipher,'SYNTHETIC-password-only-123')
    try:
        restored=ListingStore(restored_path)
        assert restored.list('internal')==store.list('internal')
        assert restored.decisions('internal')==store.decisions('internal')
        assert restored.export_provenance('internal')==store.export_provenance('internal')
        assert restored.scan_status('internal')==store.scan_status('internal')
        assert restored.ingest(parse_p0_csv(p0_payload(2),now=NOW),'internal','synthetic-p0')['skipped']
        monkeypatch.delenv('SCANNER_DATABASE',raising=False)
        app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py')
        app.session_state['_restored_database']=restored_path
        app.run();app.radio[0].set_value('import').run()
        assert not app.exception
        assert sum('GESPERRTER RECHERCHEHINWEIS' in w.value for w in app.warning)==2
        assert any('Sitzungskopie' in c.value for c in app.caption)
    finally:shutil.rmtree(Path(restored_path).parent)


def test_wrong_password_tamper_and_plain_sqlite_rejected(tmp_path):
    store=prepared(tmp_path);cipher=encrypted_backup(store,'SYNTHETIC-password-only-123')
    for value,password in [(cipher,'wrong-synthetic-password'),(cipher[:-1]+bytes([cipher[-1]^1]),'SYNTHETIC-password-only-123'),(Path(store.path).read_bytes(),'SYNTHETIC-password-only-123'),(b'x'*(2*1024*1024+1),'SYNTHETIC-password-only-123')]:
        with pytest.raises(ValidationError):restore_encrypted(value,password)
    assert len(store.list('internal'))==3
    with pytest.raises(ValidationError):encrypted_backup(store,'short')


def test_backup_rejects_extra_sqlite_objects_and_p0_saved_candidate(tmp_path):
    store=prepared(tmp_path)
    with store.connect() as db:db.execute('CREATE VIEW unexpected AS SELECT * FROM listings')
    with pytest.raises(ValidationError):store.backup(tmp_path/'bad.sqlite3')
    with store.connect() as db:
        db.execute('DROP VIEW unexpected')
        lot=next(lot for lot in store.list('internal') if lot.terms_reference.startswith('P0:'))
        db.execute('INSERT OR REPLACE INTO decisions VALUES (?,?,?,?,?,?)',('internal',lot.source,lot.source_id,'candidate','Synthetic invalid decision',lot.observed_at))
    assert not candidate_export(store,'internal')['candidates']
    with pytest.raises(ValidationError):store.backup(tmp_path/'bad-decision.sqlite3')


def test_p0_api_and_contract_cannot_be_promoted_even_with_mutated_status(tmp_path):
    lot=parse_p0_csv(p0_payload(1),now=NOW).listings[0]
    mutated=replace(lot,status='active')
    assert any('P0' in b for b in assess_listing(mutated,Assumptions(),review_confirmed=True,now=NOW)['blockers'])
    envelope={'schema_version':1,'event_type':'opportunity.selected','generated_at':NOW.isoformat(),'selection_kind':'manual_not_profit_verified',
              'candidates':[{'offer_key':list(lot.key),'approved_snapshot_at':lot.observed_at,'approval_status':'manually_selected','listing':mutated.to_dict()}]}
    with pytest.raises(ValidationError,match='P0'):validate_candidate_export(envelope,NOW)


def test_storage_and_source_navigation_without_database(monkeypatch):
    monkeypatch.delenv('SCANNER_DATABASE',raising=False)
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py')
    app.session_state['section']='Speicher';app.run()
    assert not app.exception
    assert any('Sitzungsvorschau' in i.value for i in app.info)
    assert not app.radio
    app.session_state['section']='Quellen';app.run()
    assert not app.exception
    assert len(app.expander)==21
    assert app.expander[0].label=='Kernquelle · RESTLOS'
    assert not app.get('file_uploader')


def test_manual_risk_hurdle_increases_target_without_changing_costs():
    a=Assumptions(target_margin=.1)
    adjusted=risk_adjusted_assumptions(a,.05,.1,'Synthetic risk method')
    assert adjusted.target_margin==pytest.approx(.3)
    assert adjusted.transport==a.transport
    for args in [(None,0,'method'),(.5,.5,'method'),(0,0,'')]:
        with pytest.raises(ValueError):risk_adjusted_assumptions(a,*args)


def test_import_status_preserves_unknown_times_and_repeat_counts(tmp_path):
    store=prepared(tmp_path)
    rows=store.import_status('internal')
    assert len(rows)==2 and all(row['imported_at'] is None for row in rows)
    assert sum(row['provenance_rows'] for row in rows)==2
    assert store.import_status('other')==()


def test_restore_with_wrong_password_has_no_database_side_effect(tmp_path):
    store=prepared(tmp_path)
    before=Path(store.path).read_bytes()
    cipher=encrypted_backup(store,'SYNTHETIC-password-only-123')
    with pytest.raises(ValidationError):restore_encrypted(cipher,'SYNTHETIC-wrong-password')
    assert Path(store.path).read_bytes()==before


def test_unauthorized_user_never_gets_backup_or_navigation_controls(monkeypatch):
    monkeypatch.setenv('SCANNER_ACCESS_MODE','private')
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py')
    app.run()
    assert not app.exception
    assert not app.get('file_uploader') and not app.get('download_button')
    assert not app.text_input and not app.get('pills')


def test_corrupt_configured_database_does_not_hide_restore_ui(tmp_path,monkeypatch):
    bad=tmp_path/'corrupt.sqlite3';bad.write_bytes(b'SYNTHETIC corrupt bytes')
    monkeypatch.setenv('SCANNER_DATABASE',str(bad))
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py')
    app.session_state['section']='Speicher';app.run()
    assert not app.exception and app.error
    assert app.get('file_uploader')
    assert any(button.label=='Backup prüfen und Sitzungskopie öffnen' for button in app.button)
    assert not any(button.label=='Verschlüsselte Sicherung erstellen' for button in app.button)
    assert bad.read_bytes()==b'SYNTHETIC corrupt bytes'


def test_restore_picker_has_no_extension_filter(monkeypatch):
    monkeypatch.delenv('SCANNER_DATABASE',raising=False)
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py')
    app.session_state['section']='Speicher';app.run()
    assert not app.exception
    uploaders=app.get('file_uploader')
    assert len(uploaders)==1
    assert uploaders[0].proto.id.endswith('-restore_upload')
    assert list(uploaders[0].proto.type)==[]
    restore=next(button for button in app.button if button.label=='Backup prüfen und Sitzungskopie öffnen')
    assert restore.disabled


@pytest.mark.parametrize('payload',[
    b'',
    b'%PDF-1.7\n'+b'SYNTHETIC invalid upload'*10,
    b'SQLite format 3\x00'+b'SYNTHETIC plaintext'*10,
    HEADER+b'\x00'*100,
])
def test_unfiltered_restore_rejects_invalid_contents_without_touching_store(tmp_path,payload):
    store=prepared(tmp_path)
    before=Path(store.path).read_bytes()
    with pytest.raises(ValidationError):
        restore_encrypted(payload,'SYNTHETIC-password-only-123')
    assert Path(store.path).read_bytes()==before
