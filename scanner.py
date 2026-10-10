"""Automatic processing of an authorised file inbox; no remote auction fetch."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from listings import Listing, ValidationError, identifier, timestamp
from imports import MAX_BYTES, parse_import


class ListingStore:
    def __init__(self, path):
        self.path = str(path)
        # New stores contain private business data; owner-only file permissions.
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        with closing(self.connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS listings (workspace TEXT, source TEXT, source_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(workspace, source, source_id))")
            db.execute("CREATE TABLE IF NOT EXISTS imports (workspace TEXT, digest TEXT, PRIMARY KEY(workspace, digest))")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def ingest(self, batch, workspace, digest):
        identifier(workspace, "workspace")
        counts = dict(inserted=0, updated=0, unchanged=0)
        with closing(self.connect()) as db, db:
            # Serialise read/compare/write to prevent concurrent regression.
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM imports WHERE workspace=? AND digest=?", (workspace, digest)).fetchone():
                return dict(skipped=True, **counts)
            for lot in batch.listings:
                args = (workspace, lot.source, lot.source_id)
                old = db.execute("SELECT payload FROM listings WHERE workspace=? AND source=? AND source_id=?", args).fetchone()
                if old:
                    previous = Listing.parse(json.loads(old[0]))
                    before, after = timestamp(previous.observed_at, "observed_at"), timestamp(lot.observed_at, "observed_at")
                    if before == after and previous != lot:
                        raise ValidationError("Widersprüchliche Dublette im Speicher")
                    if before >= after:
                        counts["unchanged"] += 1
                        continue
                db.execute("INSERT OR REPLACE INTO listings VALUES (?, ?, ?, ?)", (*args, json.dumps(lot.to_dict(), ensure_ascii=False)))
                counts["updated" if old else "inserted"] += 1
            db.execute("INSERT INTO imports VALUES (?, ?)", (workspace, digest))
        return dict(skipped=False, **counts)

    def list(self, workspace):
        identifier(workspace, "workspace")
        with closing(self.connect()) as db:
            rows = db.execute("SELECT payload FROM listings WHERE workspace=? ORDER BY source, source_id", (workspace,)).fetchall()
        try:
            return tuple(Listing.parse(json.loads(row[0])) for row in rows)
        except (ValueError, TypeError, RecursionError):
            raise ValidationError("Scanner-Speicher enthält ungültige Daten") from None


def scan_inbox(inbox, store, workspace):
    """One bounded pass. Invalid files isolated; every valid file is atomic."""
    identifier(workspace, "workspace")
    folder = Path(inbox)
    if not folder.is_dir():
        raise ValidationError("Import-Ordner fehlt")
    results = []
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".json", ".csv"})
    if len(paths) > 100:
        raise ValidationError("Maximal 100 Dateien pro Inbox; verarbeitete Dateien archivieren")
    for path in paths:
        try:
            if path.is_symlink() or not path.is_file():
                raise ValidationError("Nur reguläre Dateien, keine Symlinks")
            with path.open("rb") as file:
                payload = file.read(MAX_BYTES + 1)
            batch = parse_import(payload, path.suffix[1:].lower())
            result = store.ingest(batch, workspace, hashlib.sha256(payload).hexdigest())
            results.append(dict(file=path.name, status="ok", duplicates=batch.duplicates, **result))
        except (OSError, ValueError, sqlite3.Error):
            # Do not echo input values, credentials, or database details in logs.
            results.append(dict(file=path.name, status="error", error="Datei ungültig oder Speicher nicht verfügbar"))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inbox", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--workspace", default="internal")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args(argv)
    if args.interval < 60:
        parser.error("Intervall mindestens 60 Sekunden")
    try:
        identifier(args.workspace, "workspace")
        store = ListingStore(args.database)
        while True:
            results = scan_inbox(args.inbox, store, args.workspace)
            print(json.dumps(results, ensure_ascii=False), flush=True)
            if not args.watch:
                return 1 if any(r["status"] == "error" for r in results) else 0
            time.sleep(args.interval)
    except (OSError, ValueError, sqlite3.Error):
        print("Scanner konnte nicht gestartet werden; Konfiguration/Speicher prüfen")
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
