"""Private, offline P0 acceptance probe. No source requests or business execution."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_import import parse_p0_csv,p0_import_digest
from scanner import ListingStore,restore_backup
from assessment import assess_listing
from scoring import Assumptions


def validate(csv_path,evidence_path,database,confirmation_context):
    started=time.perf_counter()
    payload=Path(csv_path).read_bytes();proof=Path(evidence_path).read_bytes()
    batch=parse_p0_csv(payload,proof,hammer_confirmation=confirmation_context)
    digest=p0_import_digest(payload,proof,confirmation_context)
    store=ListingStore(database)
    first=store.ingest(batch,'internal',digest)
    repeated=store.ingest(parse_p0_csv(payload,proof,hammer_confirmation=confirmation_context),'internal',digest)
    rows=store.import_provenance('internal',digest)
    assert rows==batch.provenance or first['skipped']
    keys={lot.key for lot in batch.listings}
    listings=tuple(lot for lot in store.list('internal') if lot.key in keys)
    assessments=[assess_listing(lot,Assumptions(sale_tax_mode='regular'),review_confirmed=True) for lot in listings]
    with tempfile.TemporaryDirectory(prefix='private-p0-backup-') as folder:
        store.backup(Path(folder)/'backup.sqlite3')
        restored=ListingStore(restore_backup(Path(folder)/'backup.sqlite3',Path(folder)/'restored.sqlite3'))
        assert restored.export_provenance('internal')==store.export_provenance('internal')
        assert restored.list('internal')==store.list('internal')
    # Test actual app.py rendering behind the existing gate using a synthetic
    # authorized identity, without reading/changing real OIDC secrets or a host.
    import streamlit
    from streamlit.testing.v1 import AppTest
    fake_user=SimpleNamespace(is_logged_in=True,to_dict=lambda:{'iss':'https://identity.example.org','sub':'synthetic-p0-ui-check'})
    with patch.dict(os.environ,{'SCANNER_ACCESS_MODE':'private','SCANNER_DATABASE':str(database),'SCANNER_WORKSPACE':'internal'}), patch.object(streamlit,'user',fake_user):
        app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=30)
        app.secrets['auth']={name:'synthetic-config-only' for name in ('redirect_uri','cookie_secret','client_id','client_secret','server_metadata_url')}
        app.secrets['scanner']={'allowed_identities':[{'issuer':'https://identity.example.org','subject':'synthetic-p0-ui-check'}]}
        app.run();app.radio[0].set_value('import').run()
        assert not app.exception
        shown=sum('GESPERRTER RECHERCHEHINWEIS' in warning.value for warning in app.warning)
        assert shown>=len(listings)
        assert not any('candidate' in select.options for select in app.selectbox if select.label=='Entscheidung')
    documented=len({tuple(row['source_key']) for row in rows if row['evidence'] and row['evidence']['rights_status']=='documented'})
    return dict(input_kind='real_user_supplied_research',csv_sha256=sha256(payload).hexdigest(),evidence_sha256=sha256(proof).hexdigest(),
        rows=len(batch.listings),duplicates_in_file=batch.duplicates,first_import=first,repeat_import=repeated,
        persisted_research_hints=len(listings),original_evidence_rows=sum(row.get('original_evidence_row') is not None for row in rows),
        user_confirmed_hammer_prices=sum(row['price']['kind']=='hammer' for row in rows),
        documented_rights_records= documented,independently_documented_hammer_prices=sum(bool(row['evidence'] and row['evidence']['hammer_verification']=='documented') for row in rows),
        missing_source_times=sum(row['source_observed_at'] is None for row in rows),
        statuses=dict(Counter(lot.status for lot in listings)),blocked_assessments=sum(a['status']=='blocked' for a in assessments),
        financial_values_unknown=all(d.value is None for lot in listings for d in lot.fields.values()),
        purchase_candidates=len(store.export_candidates('internal')),backup_restore_equal=True,dashboard_blocked_cards=shown,
        dashboard_verification='Streamlit AppTest, existing private gate with synthetic authorized identity; no real Google login',
        ten_rights_documented_records_met=documented>=10,p0_legal_acceptance='NOT_MET' if documented<10 else 'MANUAL_REVIEW_REQUIRED',elapsed_seconds=time.perf_counter()-started)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('csv','evidence','database','confirmation-context','report'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    result=validate(args.csv,args.evidence,args.database,args.confirmation_context)
    # New private file only; never overwrite previous acceptance evidence.
    fd=os.open(args.report,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as handle:json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
