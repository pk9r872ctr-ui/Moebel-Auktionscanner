"""Reproducible synthetic integration probe; never processes real auctions."""
import sys,time,tempfile,json,csv,io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_import import parse_research_csv,REQUIRED_COLUMNS,OPTIONAL_COLUMNS
from scanner import ListingStore,restore_backup
from validation_metrics import practice_metrics
from extended_economics import assess_extended
from scoring import Assumptions
from datetime import datetime,timezone
started=time.perf_counter(); out=io.StringIO()
w=csv.DictWriter(out,fieldnames=REQUIRED_COLUMNS+OPTIONAL_COLUMNS,delimiter=';');w.writeheader()
for i in range(20):
 w.writerow(dict(source='synthetic-source',source_id=f'test-{i}',title=f'TEST ONLY: {i+1} Stück Stuhl',listing_url=f'https://example.org/test/{i}',observed_at=datetime.now(timezone.utc).isoformat(),rights_reference='Entirely fabricated test data',currency='EUR',price=i*10,price_kind='current',description='TEST ONLY original description'))
batch=parse_research_csv(out.getvalue().encode())
with tempfile.TemporaryDirectory() as folder:
 store=ListingStore(Path(folder)/'db.sqlite3')
 first=store.ingest(batch,'internal','synthetic-sha-test')
 repeat=store.ingest(batch,'internal','synthetic-sha-test')
 store.backup(Path(folder)/'backup.sqlite3')
 restored=ListingStore(restore_backup(Path(folder)/'backup.sqlite3',Path(folder)/'restored.sqlite3'))
 assert len(restored.list('internal'))==20 and len(restored.export_provenance('internal')[0]['provenance'])==20
 report=practice_metrics(store.list('internal'),input_count=20,elapsed_seconds=time.perf_counter()-started,assessments=[assess_extended(lot,Assumptions(),None) for lot in batch.listings])
 report.update(first_import=first,repeat_import=repeat,backup_restore_preserved=20,real_offers_processed=0)
 # No private data or database survives this explicitly synthetic run.
 print(json.dumps(report))
