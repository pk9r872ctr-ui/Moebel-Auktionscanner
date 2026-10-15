"""Automatic processing of an authorised file inbox; no remote auction fetch."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from datetime import datetime, timezone
from listings import Listing, ValidationError, identifier, timestamp
from imports import MAX_BYTES, parse_import


class ListingStore:
    def __init__(self, path):
        self.path = str(path)
        if Path(self.path).is_symlink():
            raise ValidationError("Speicherpfad darf kein Symlink sein")
        # New stores contain private business data; owner-only file permissions.
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS listings (workspace TEXT, source TEXT, source_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(workspace, source, source_id))")
            db.execute("CREATE TABLE IF NOT EXISTS imports (workspace TEXT, digest TEXT, PRIMARY KEY(workspace, digest))")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 2:
                raise ValidationError("Speicherversion neuer als unterstützte Version")
            db.execute("CREATE TABLE IF NOT EXISTS observations (workspace TEXT, source TEXT, source_id TEXT, observed_at TEXT, payload TEXT NOT NULL, PRIMARY KEY(workspace, source, source_id, observed_at))")
            db.execute("CREATE TABLE IF NOT EXISTS decisions (workspace TEXT, source TEXT, source_id TEXT, decision TEXT NOT NULL, note TEXT NOT NULL, observed_at TEXT NOT NULL, PRIMARY KEY(workspace, source, source_id))")
            db.execute("CREATE TABLE IF NOT EXISTS scan_runs (id INTEGER PRIMARY KEY, workspace TEXT NOT NULL, finished_at TEXT NOT NULL, results TEXT NOT NULL)")
            if version == 0:
                for workspace, source, source_id, payload in db.execute("SELECT * FROM listings").fetchall():
                    lot = Listing.parse(json.loads(payload))
                    observed_at = timestamp(lot.observed_at, "observed_at").isoformat()
                    db.execute("INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?, ?)", (workspace, source, source_id, observed_at, payload))
                db.execute("PRAGMA user_version=1")
            if version < 2:
                db.execute("CREATE TABLE import_provenance (workspace TEXT, digest TEXT, payload TEXT NOT NULL, PRIMARY KEY(workspace,digest))")
                db.execute("PRAGMA user_version=2")
            db.execute("CREATE TRIGGER IF NOT EXISTS observations_no_update BEFORE UPDATE ON observations BEGIN SELECT RAISE(ABORT, 'immutable observation'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS observations_no_delete BEFORE DELETE ON observations BEGIN SELECT RAISE(ABORT, 'immutable observation'); END")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def ingest(self, batch, workspace, digest):
        identifier(workspace, "workspace")
        if not isinstance(digest, str) or not digest or len(digest) > 256:
            raise ValidationError("Importdigest erforderlich, maximal 256 Zeichen")
        provenance = _encode_provenance(getattr(batch, "provenance", ()))
        counts = dict(inserted=0, updated=0, unchanged=0)
        with closing(self.connect()) as db, db:
            # Serialise read/compare/write to prevent concurrent regression.
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM imports WHERE workspace=? AND digest=?", (workspace, digest)).fetchone():
                return dict(skipped=True, **counts)
            for lot in batch.listings:
                # Validate even programmatically constructed batches; preserve originals.
                lot = Listing.parse(lot.to_dict())
                payload = json.dumps(lot.to_dict(), ensure_ascii=False)
                observed_at = timestamp(lot.observed_at, "observed_at").isoformat()
                args = (workspace, lot.source, lot.source_id)
                observed = db.execute("SELECT payload FROM observations WHERE workspace=? AND source=? AND source_id=? AND observed_at=?", (*args, observed_at)).fetchone()
                if observed and Listing.parse(json.loads(observed[0])) != lot:
                    raise ValidationError("Widersprüchliche Dublette in Beobachtungshistorie")
                db.execute("INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?, ?)", (*args, observed_at, payload))
                old = db.execute("SELECT payload FROM listings WHERE workspace=? AND source=? AND source_id=?", args).fetchone()
                if old:
                    previous = Listing.parse(json.loads(old[0]))
                    if lot.terms_reference.startswith("P0:") and not previous.terms_reference.startswith("P0:"):
                        raise ValidationError("P0-Recherche kollidiert mit vorhandenem Angebot; manuelle Prüfung erforderlich")
                    before, after = timestamp(previous.observed_at, "observed_at"), timestamp(lot.observed_at, "observed_at")
                    if before == after and previous != lot:
                        raise ValidationError("Widersprüchliche Dublette im Speicher")
                    if before >= after:
                        counts["unchanged"] += 1
                        continue
                db.execute("INSERT OR REPLACE INTO listings VALUES (?, ?, ?, ?)", (*args, json.dumps(lot.to_dict(), ensure_ascii=False)))
                counts["updated" if old else "inserted"] += 1
            db.execute("INSERT INTO imports VALUES (?, ?)", (workspace, digest))
            if provenance != "[]":
                db.execute("INSERT INTO import_provenance VALUES (?, ?, ?)", (workspace, digest, provenance))
        return dict(skipped=False, **counts)

    def list(self, workspace):
        identifier(workspace, "workspace")
        with closing(self.connect()) as db:
            rows = db.execute("SELECT payload FROM listings WHERE workspace=? ORDER BY source, source_id", (workspace,)).fetchall()
        try:
            return tuple(Listing.parse(json.loads(row[0])) for row in rows)
        except (ValueError, TypeError, RecursionError):
            raise ValidationError("Scanner-Speicher enthält ungültige Daten") from None

    def history(self, workspace, source, source_id):
        keys = self._keys(workspace, source, source_id)
        with closing(self.connect()) as db:
            rows = db.execute("SELECT payload FROM observations WHERE workspace=? AND source=? AND source_id=? ORDER BY observed_at", keys).fetchall()
        return tuple(Listing.parse(json.loads(row[0])) for row in rows)

    @staticmethod
    def _keys(workspace, source, source_id):
        return tuple(identifier(v, n) for v, n in zip((workspace, source, source_id), ("workspace", "source", "source_id")))

    def set_decision(self, workspace, source, source_id, decision, note="", *, expected_observed_at=None):
        keys = self._keys(workspace, source, source_id)
        if not isinstance(decision, str) or decision not in {"watchlist", "candidate", "rejected", "unreviewed"}:
            raise ValidationError("Ungültiger Entscheidungsstatus")
        if not isinstance(note, str) or len(note) > 2000 or any(ord(c) < 32 for c in note):
            raise ValidationError("Ungültige Entscheidungsnotiz")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM listings WHERE workspace=? AND source=? AND source_id=?", keys).fetchone()
            if not row:
                raise ValidationError("Angebot nicht im Arbeitsbereich vorhanden")
            lot = Listing.parse(json.loads(row[0]))
            observed_at = timestamp(lot.observed_at, "observed_at").isoformat()
            if decision == "candidate" and (lot.terms_reference.startswith("P0:") or self.p0_provenance(workspace, lot)):
                raise ValidationError("Historische P0-Recherche ist kein Einkaufskandidat")
            if expected_observed_at is not None and timestamp(expected_observed_at, "expected_observed_at").isoformat() != observed_at:
                raise ValidationError("Angebot seit Anzeige geändert; aktuellen Stand erneut prüfen")
            db.execute("INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?, ?, ?)", (*keys, decision, note, observed_at))

    def decisions(self, workspace):
        identifier(workspace, "workspace")
        with closing(self.connect()) as db:
            rows = db.execute("SELECT d.source,d.source_id,d.decision,d.note,d.observed_at,l.payload FROM decisions d JOIN listings l USING(workspace,source,source_id) WHERE d.workspace=? ORDER BY d.source,d.source_id", (workspace,)).fetchall()
        result = []
        for source, source_id, decision, note, observed_at, payload in rows:
            current = timestamp(Listing.parse(json.loads(payload)).observed_at, "observed_at").isoformat()
            stale = observed_at != current
            result.append(dict(source=source, source_id=source_id, decision=decision, note=note, observed_at=observed_at, stale=stale, review_required=stale))
        return tuple(result)

    def export_listings(self, workspace):
        return tuple(lot.to_dict() for lot in self.list(workspace))

    def export_candidates(self, workspace):
        # Read snapshots and decisions in one transaction to prevent approved-update races.
        identifier(workspace, "workspace")
        with closing(self.connect()) as db:
            rows = db.execute("SELECT l.payload,d.observed_at FROM listings l JOIN decisions d USING(workspace,source,source_id) WHERE l.workspace=? AND d.decision='candidate' ORDER BY l.source,l.source_id", (workspace,)).fetchall()
        result = []
        for payload, approved_at in rows:
            lot = Listing.parse(json.loads(payload))
            if timestamp(lot.observed_at, "observed_at").isoformat() == approved_at and not lot.terms_reference.startswith("P0:") and not self.p0_provenance(workspace, lot):
                result.append(lot.to_dict())
        return tuple(result)

    def import_provenance(self, workspace, digest):
        identifier(workspace, "workspace")
        if not isinstance(digest, str) or not digest or len(digest) > 256:
            raise ValidationError("Ungültiger Importdigest")
        with closing(self.connect()) as db:
            row = db.execute("SELECT payload FROM import_provenance WHERE workspace=? AND digest=?", (workspace, digest)).fetchone()
        return tuple(json.loads(row[0])) if row else ()

    def export_provenance(self, workspace):
        identifier(workspace, "workspace")
        with closing(self.connect()) as db:
            rows = db.execute("SELECT digest,payload FROM import_provenance WHERE workspace=? ORDER BY digest", (workspace,)).fetchall()
        return tuple(dict(digest=digest, provenance=json.loads(payload)) for digest, payload in rows)

    def p0_provenance(self, workspace, lot):
        """Read existing sidecars; no schema change or source fetch."""
        return tuple(row for entry in self.export_provenance(workspace) for row in entry["provenance"]
                     if row.get("p0_research") is True and row.get("source_key") == list(lot.key)
                     and row.get("observed_at") == lot.observed_at)

    def import_status(self, workspace):
        identifier(workspace, "workspace")
        with closing(self.connect()) as db:
            rows=db.execute("SELECT i.digest,p.payload FROM imports i LEFT JOIN import_provenance p USING(workspace,digest) WHERE i.workspace=? ORDER BY i.digest",(workspace,)).fetchall()
        return tuple({"digest":digest,"provenance_rows":len(json.loads(payload)) if payload else 0,
                      "imported_at":None} for digest,payload in rows)

    def record_scan(self, workspace, results):
        identifier(workspace, "workspace")
        with closing(self.connect()) as db, db:
            db.execute("INSERT INTO scan_runs(workspace,finished_at,results) VALUES (?,?,?)", (workspace, datetime.now(timezone.utc).isoformat(), json.dumps(results, ensure_ascii=False)))

    def scan_status(self, workspace, limit=20):
        identifier(workspace, "workspace")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValidationError("Statuslimit 1–100 erforderlich")
        with closing(self.connect()) as db:
            rows = db.execute("SELECT id,finished_at,results FROM scan_runs WHERE workspace=? ORDER BY id DESC LIMIT ?", (workspace, limit)).fetchall()
        return tuple(dict(id=i, finished_at=t, results=json.loads(r)) for i,t,r in rows)

    def backup(self, destination):
        return _copy_database(self.path, destination)

    @staticmethod
    def restore_backup(source, destination):
        return restore_backup(source, destination)


def _encode_provenance(value):
    if not isinstance(value, (list, tuple)) or any(not isinstance(row, dict) for row in value):
        raise ValidationError("Recherche-Provenienz muss eine Liste von Objekten sein")
    try:
        payload = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise ValidationError("Recherche-Provenienz enthält ungültige Werte") from None
    if len(payload.encode("utf-8")) > MAX_BYTES:
        raise ValidationError("Recherche-Provenienz überschreitet Importlimit")
    return payload


def _validate_database(path):
    # Read-only validation avoids changing an unknown/corrupted backup.
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        db.set_progress_handler(lambda: 1, 2_000_000)
        allowed_tables={"listings","imports","observations","decisions","scan_runs","import_provenance"}
        for kind,name,sql in db.execute("SELECT type,name,sql FROM sqlite_master"):
            if kind=="table" and (name not in allowed_tables or "virtual table" in (sql or "").lower()):
                raise ValidationError("Backup enthält nicht unterstützte Tabellen")
            if kind=="view" or (kind=="index" and not name.startswith("sqlite_autoindex_")):
                raise ValidationError("Backup enthält nicht unterstützte Schemaobjekte")
            if kind=="trigger":
                action={"observations_no_update":"UPDATE", "observations_no_delete":"DELETE"}.get(name)
                expected=f"CREATE TRIGGER {name} BEFORE {action} ON observations BEGIN SELECT RAISE(ABORT, 'immutable observation'); END"
                # sqlite_master omits IF NOT EXISTS on some SQLite releases.
                actual=" ".join((sql or "").replace("IF NOT EXISTS ", "").split()).rstrip(";").lower()
                if action is None or actual != " ".join(expected.split()).lower():
                    raise ValidationError("Backup enthält unerwartete Trigger")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValidationError("Datenbankintegritätsprüfung fehlgeschlagen")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, 2):
            raise ValidationError("Nicht unterstützte Speicherversion")
        for table in ("listings", "imports"):
            db.execute("SELECT * FROM " + table + " LIMIT 0")
        for workspace, source, source_id, payload in db.execute("SELECT * FROM listings"):
            ListingStore._keys(workspace, source, source_id)
            lot = Listing.parse(json.loads(payload))
            if (lot.source, lot.source_id) != (source, source_id):
                raise ValidationError("Angebotskennung im Speicher widersprüchlich")
        if version >= 1:
            for table in ("observations", "decisions", "scan_runs"):
                db.execute("SELECT * FROM " + table + " LIMIT 0")
            for workspace, source, source_id, observed_at, payload in db.execute("SELECT * FROM observations"):
                ListingStore._keys(workspace, source, source_id)
                lot = Listing.parse(json.loads(payload))
                if (lot.source, lot.source_id) != (source, source_id) or timestamp(lot.observed_at, "observed_at") != timestamp(observed_at, "observed_at"):
                    raise ValidationError("Beobachtungshistorie widersprüchlich")
            for workspace, source, source_id, payload in db.execute("SELECT * FROM listings"):
                lot = Listing.parse(json.loads(payload))
                observed_at = timestamp(lot.observed_at, "observed_at").isoformat()
                latest = db.execute("SELECT observed_at,payload FROM observations WHERE workspace=? AND source=? AND source_id=? ORDER BY observed_at DESC LIMIT 1", (workspace, source, source_id)).fetchone()
                if not latest or latest[0] != observed_at or Listing.parse(json.loads(latest[1])) != lot:
                    raise ValidationError("Aktueller Stand widerspricht Beobachtungshistorie")
            for workspace, source, source_id, decision, note, observed_at in db.execute("SELECT * FROM decisions"):
                ListingStore._keys(workspace, source, source_id)
                if decision not in {"watchlist", "candidate", "rejected", "unreviewed"} or not isinstance(note, str) or len(note) > 2000:
                    raise ValidationError("Entscheidungsdaten ungültig")
                if decision == "candidate":
                    current=db.execute("SELECT payload FROM listings WHERE workspace=? AND source=? AND source_id=?",(workspace,source,source_id)).fetchone()
                    if current and Listing.parse(json.loads(current[0])).terms_reference.startswith("P0:"):
                        raise ValidationError("Backup enthält unzulässigen P0-Kandidaten")
                if not db.execute("SELECT 1 FROM observations WHERE workspace=? AND source=? AND source_id=? AND observed_at=?", (workspace, source, source_id, observed_at)).fetchone():
                    raise ValidationError("Entscheidung ohne Beobachtungsreferenz")

        if version >= 2:
            for workspace, digest, payload in db.execute("SELECT * FROM import_provenance"):
                identifier(workspace, "workspace")
                _encode_provenance(json.loads(payload))
                if not db.execute("SELECT 1 FROM imports WHERE workspace=? AND digest=?", (workspace, digest)).fetchone():
                    raise ValidationError("Provenienz ohne Importreferenz")


def _copy_database(source, destination):
    destination = Path(destination)
    _validate_database(source)
    # Exclusive creation rejects existing files, directories and symlinks.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True)) as src, closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
        _validate_database(destination)
    except Exception:
        destination.unlink()
        raise
    return destination


def restore_backup(source, destination):
    """Restore into a NEW private path only; never overwrite a running store."""
    result = _copy_database(source, destination)
    try:
        ListingStore(result)  # Migrate legacy backups only after copying.
    except Exception:
        result.unlink()
        raise
    return result


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
    store.record_scan(workspace, results)
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
