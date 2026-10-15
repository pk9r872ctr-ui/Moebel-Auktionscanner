"""SYNTHETIC ONLY: no real grants, auction results or uploaded source data."""
import csv
import io
import json
from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone
import pytest
from streamlit.testing.v1 import AppTest
from research_import import P0_COLUMNS, P0_CORE_SOURCES, parse_p0_csv, p0_import_digest
from scanner import ListingStore, restore_backup
from assessment import assess_listing
from scoring import Assumptions
from listings import ValidationError
from registry import load_registry

NOW = datetime(2026,10,15,12,tzinfo=timezone.utc)


def payload(count=10):
    out=io.StringIO();writer=csv.DictWriter(out,P0_COLUMNS,delimiter=';');writer.writeheader()
    for index in range(count):
        writer.writerow(dict(zip(P0_COLUMNS, ('Zoll-Auktion',str(index+1),'SYNTHETIC ONLY furniture '+str(index),
            'Teststadt','100','2026-07-03','beendet',f'https://www.zoll-auktion.de/auktion/produkt/{index+1}',
            'SYNTHETIC original disclaimer: kein gesicherter Zuschlag'))))
    return out.getvalue().encode('utf-8-sig')


def evidence(data):
    return dict(schema_version=1,csv_sha256=sha256(data).hexdigest(),entries=[dict(
        source='zoll-auktion',source_id='1',rights_status='documented',rights_scope='internal_commercial_import',
        rights_reference='SYNTHETIC grant only',reviewed_by='SYNTHETIC reviewer',reviewed_at='2026-10-14T12:00:00Z',
        source_observed_at=None,time_reference=None,hammer_verification='unknown',hammer_reference=None)])


def test_original_confirmation_and_missing_evidence_stay_separate():
    batch=parse_p0_csv(payload(),hammer_confirmation='SYNTHETIC user statement',now=NOW)
    row=batch.provenance[0];lot=batch.listings[0]
    assert row['original_row']['datenhinweis'].endswith('kein gesicherter Zuschlag')
    assert row['price']['kind']=='hammer' and row['price']['value']==100
    assert row['user_confirmation']['basis']=='user_statement' and row['evidence'] is None
    assert row['observed_at_kind']=='import_receipt_only'
    assert all(d.value is None and d.origin=='unknown' for d in lot.fields.values())
    assert lot.ends_at is None and lot.status=='ended' and lot.bid_kind=='unknown'
    assert assess_listing(lot,Assumptions(sale_tax_mode='regular'),review_confirmed=True,now=NOW)['status']=='blocked'


def test_evidence_is_bound_to_file_not_user_confirmation():
    data=payload();raw=evidence(data)
    batch=parse_p0_csv(data,json.dumps(raw).encode(),hammer_confirmation='SYNTHETIC user statement',now=NOW)
    assert batch.provenance[0]['evidence']['rights_status']=='documented'
    assert batch.provenance[1]['evidence'] is None
    assert 'Zuschlagspreis nicht unabhängig belegt' in batch.provenance[0]['review_issues']
    assert batch.listings[0].status=='ended'
    raw['csv_sha256']='wrong'
    with pytest.raises(ValidationError):parse_p0_csv(data,json.dumps(raw).encode(),now=NOW)
    assert p0_import_digest(data)!=p0_import_digest(data,hammer_confirmation='SYNTHETIC user statement')


@pytest.mark.parametrize('change',[{'rights_scope':None},{'rights_reference':None},{'reviewed_at':None},
    {'rights_status':[]},{'reviewed_at':'2027-01-01T00:00:00Z'},
    {'hammer_verification':'documented','hammer_reference':None},
    {'source_observed_at':'2026-10-14T12:00:00Z','time_reference':None}])
def test_invalid_evidence_is_controlled(change):
    data=payload();raw=evidence(data);raw['entries'][0].update(change)
    with pytest.raises(ValidationError):parse_p0_csv(data,json.dumps(raw).encode(),now=NOW)


def test_ten_synthetic_records_persist_repeat_restore_and_dashboard(tmp_path,monkeypatch):
    data=payload();batch=parse_p0_csv(data,hammer_confirmation='SYNTHETIC statement',now=NOW)
    store=ListingStore(tmp_path/'p0.sqlite3');digest=p0_import_digest(data,hammer_confirmation='SYNTHETIC statement')
    assert store.ingest(batch,'internal',digest)['inserted']==10
    assert store.ingest(batch,'internal',digest)['skipped']
    assert len(store.list('internal'))==10
    assert store.import_provenance('internal',digest)==batch.provenance
    assert len(store.history('internal','zoll-auktion','1'))==1
    with pytest.raises(ValidationError,match='kein Einkaufskandidat'):
        store.set_decision('internal','zoll-auktion','1','candidate')
    store.set_decision('internal','zoll-auktion','1','watchlist')
    assert store.export_candidates('internal')==()
    store.backup(tmp_path/'backup.sqlite3')
    restored=ListingStore(restore_backup(tmp_path/'backup.sqlite3',tmp_path/'restored.sqlite3'))
    assert restored.export_provenance('internal')==store.export_provenance('internal')
    assert restored.list('internal')==store.list('internal')
    monkeypatch.setenv('SCANNER_DATABASE',store.path)
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py').run()
    app.radio[0].set_value('import').run()
    assert not app.exception
    assert len([w for w in app.warning if 'GESPERRTER RECHERCHEHINWEIS' in w.value])==10
    assert any('Rechtsbeleg fehlt' in c.value for c in app.caption)
    assert any('Quellenzeit unbelegt' in c.value for c in app.caption)
    assert any('nicht unabhängig belegt' in c.value for c in app.caption)
    assert not any('candidate' in s.options for s in app.selectbox if s.label=='Entscheidung')


def test_conflicting_original_rows_atomic_and_limits():
    data=payload(1).decode('utf-8-sig');row=data.splitlines()[1]
    with pytest.raises(ValidationError):parse_p0_csv((data+row.replace(';100;',';200;')+'\n').encode(),now=NOW)
    assert parse_p0_csv((data+row+'\n').encode(),now=NOW).duplicates==1
    with pytest.raises(ValidationError):parse_p0_csv(b'bad',now=NOW)
    with pytest.raises(ValidationError):parse_p0_csv(payload().replace(b';100;',b';NaN;'),now=NOW)


def test_sources_preserved_and_core_focus_explicit():
    assert len(load_registry()['sources'])==21
    assert P0_CORE_SOURCES==('restlos','haemmerle','proventura','netbid','zoll-auktion')



def test_evidence_update_does_not_turn_receipt_into_source_time(tmp_path):
    from datetime import timedelta
    data=payload(1);store=ListingStore(tmp_path/'p0.sqlite3')
    before=parse_p0_csv(data,now=NOW)
    store.ingest(before,'internal',p0_import_digest(data))
    raw=evidence(data);raw['entries'][0].update(source_observed_at='2026-07-02T12:00:00Z',time_reference='SYNTHETIC old source capture')
    proof=json.dumps(raw).encode()
    after=parse_p0_csv(data,proof,now=NOW+timedelta(seconds=1))
    store.ingest(after,'internal',p0_import_digest(data,proof))
    current=store.list('internal')[0]
    provenance=store.p0_provenance('internal',current)[0]
    assert provenance['source_observed_at']=='2026-07-02T12:00:00+00:00'
    assert provenance['observed_at_kind']=='import_receipt_only'
    assert provenance['observed_at']!=provenance['source_observed_at']
    assert len(store.history('internal','zoll-auktion','1'))==2
    assert len(store.export_provenance('internal'))==2
    assert provenance['evidence']['rights_status']=='documented'



def test_normalized_json_reimport_cannot_promote_p0_without_sidecar(tmp_path):
    from imports import parse_import
    original=parse_p0_csv(payload(1),now=NOW)
    normalized=json.dumps({'schema_version':1,'listings':[lot.to_dict() for lot in original.listings]}).encode()
    store=ListingStore(tmp_path/'roundtrip.sqlite3')
    store.ingest(parse_import(normalized,'json',NOW),'internal','normalized-only')
    with pytest.raises(ValidationError,match='kein Einkaufskandidat'):
        store.set_decision('internal','zoll-auktion','1','candidate')
    assert store.export_candidates('internal')==()


def register_csv(data):
    from research_import import P0_REGISTER_COLUMNS
    rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig')),delimiter=';'))
    out=io.StringIO();writer=csv.DictWriter(out,P0_REGISTER_COLUMNS,delimiter=';');writer.writeheader()
    for row in rows:
        writer.writerow(dict(**row,source_id_normalized=row['auktions_id'],
            price_kind_user_claim='hammer (SYNTHETIC user claim only)',price_kind_original_evidence='unknown',
            original_observed_at='',rights_reference='',original_price_evidence='',
            data_status='P0_BLOCKED_PROVENANCE_RIGHTS',purchase_recommendation='blocked'))
    return out.getvalue().encode('utf-8-sig')


def test_supplied_csv_register_contract_preserves_blocked_original_evidence():
    data=payload();registry=register_csv(data)
    batch=parse_p0_csv(data,registry,hammer_confirmation='SYNTHETIC statement',now=NOW)
    assert len(batch.listings)==10
    row=batch.provenance[0]
    assert row['original_evidence_row']['purchase_recommendation']=='blocked'
    assert row['original_evidence_row']['rights_reference']==''
    assert row['evidence']['rights_status']=='unknown'
    assert row['source_observed_at'] is None
    assert row['price']['kind']=='hammer'
    assert row['evidence']['hammer_verification']=='unknown'
    with pytest.raises(ValidationError):parse_p0_csv(data,registry.replace(b';100;',b';200;'),now=NOW)
    with pytest.raises(ValidationError):parse_p0_csv(data,registry.replace(b';blocked',b';approved'),now=NOW)



def test_historical_receipt_never_overwrites_existing_regular_listing(tmp_path):
    from imports import parse_import
    from test_imports import raw_listing, encode
    raw=raw_listing();raw['source']='zoll-auktion';raw['source_id']='1'
    store=ListingStore(tmp_path/'collision.sqlite3')
    existing=parse_import(encode(raw),'json',NOW)
    store.ingest(existing,'internal','existing')
    with pytest.raises(ValidationError,match='kollidiert'):
        store.ingest(parse_p0_csv(payload(1),now=NOW),'internal','p0')
    assert store.list('internal')==existing.listings
    assert store.export_provenance('internal')==()
    assert len(store.history('internal','zoll-auktion','1'))==1
