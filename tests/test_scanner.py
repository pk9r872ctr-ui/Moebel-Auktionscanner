import json
import pytest
from scanner import ListingStore, scan_inbox, main
from imports import parse_import
from listings import ValidationError
from test_imports import raw_listing, encode, NOW


def test_inbox_errors_idempotency_and_restart(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "valid.json").write_bytes(encode(raw_listing()))
    (inbox / "bad.json").write_bytes(b"bad")
    store = ListingStore(tmp_path / "scan.sqlite3")
    results = scan_inbox(inbox, store, "internal")
    assert [r["status"] for r in results] == ["error", "ok"]
    assert results[1]["inserted"] == 1
    assert scan_inbox(inbox, store, "internal")[1]["skipped"]
    assert len(ListingStore(store.path).list("internal")) == 1
    assert store.list("other") == ()
    assert main(["--inbox", str(inbox), "--database", store.path]) == 1
    (inbox / "bad.json").unlink()
    assert main(["--inbox", str(inbox), "--database", store.path]) == 0


def test_newer_update_and_older_no_regression(tmp_path):
    store = ListingStore(tmp_path / "scan.sqlite3")
    old, new = raw_listing(), raw_listing()
    new["observed_at"] = "2026-10-10T12:00:00Z"
    new["fields"]["current_bid"]["value"] = 1300
    assert store.ingest(parse_import(encode(old), "json", NOW), "a", "1")["inserted"] == 1
    assert store.ingest(parse_import(encode(new), "json", NOW), "a", "2")["updated"] == 1
    assert store.ingest(parse_import(encode(old), "json", NOW), "a", "3")["unchanged"] == 1
    assert store.list("a")[0].fields["current_bid"].value == 1300
    # Source identifiers and workspaces independently scope duplicate keys.
    assert store.ingest(parse_import(encode(new), "json", NOW), "b", "2")["inserted"] == 1


def test_store_conflict_rolls_back_whole_file(tmp_path):
    store = ListingStore(tmp_path / "scan.sqlite3")
    raw = raw_listing()
    store.ingest(parse_import(encode(raw), "json", NOW), "a", "first")
    new = raw_listing()
    new["source_id"] = "test-2"
    raw["title"] = "conflict"
    with pytest.raises(ValidationError):
        store.ingest(parse_import(encode(new, raw), "json", NOW), "a", "conflict")
    assert len(store.list("a")) == 1


def test_symlinks_and_missing_inbox(tmp_path):
    store = ListingStore(tmp_path / "scan.sqlite3")
    target = tmp_path / "outside"
    target.write_bytes(encode(raw_listing()))
    (tmp_path / "link.json").symlink_to(target)
    assert scan_inbox(tmp_path, store, "a")[0]["status"] == "error"
    with pytest.raises(ValidationError):
        scan_inbox(tmp_path / "missing", store, "a")
    assert main(["--inbox", str(tmp_path / "missing"), "--database", store.path]) == 2
    with pytest.raises(SystemExit):
        main(["--inbox", str(tmp_path), "--database", store.path, "--interval", "1"])


def test_private_database_and_corrupt_payload(tmp_path):
    import sqlite3
    store = ListingStore(tmp_path / "scan.sqlite3")
    assert (tmp_path / "scan.sqlite3").stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(store.path) as db:
        db.execute("INSERT INTO listings VALUES (?, ?, ?, ?)", ("a", "s", "1", "invalid-json"))
    with pytest.raises(ValidationError, match="ungültige Daten"):
        store.list("a")


def test_watch_reprocesses_new_content_and_stops_cleanly(tmp_path, monkeypatch, capsys):
    import scanner
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    file = inbox / "test.json"
    file.write_bytes(encode(raw_listing()))
    sleeps = []
    def next_cycle(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise KeyboardInterrupt
        updated = raw_listing()
        updated["observed_at"] = "2026-10-10T12:00:00Z"
        updated["fields"]["current_bid"]["value"] = 1300
        file.write_bytes(encode(updated))
    monkeypatch.setattr(scanner.time, "sleep", next_cycle)
    assert main(["--inbox", str(inbox), "--database", str(tmp_path / "watch.sqlite3"), "--watch"]) == 0
    reports = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert reports[0][0]["inserted"] == 1
    assert reports[1][0]["updated"] == 1
    assert sleeps == [60, 60]


def test_history_and_snapshot_bound_decisions(tmp_path):
    store = ListingStore(tmp_path / "scan.sqlite3")
    old = raw_listing()
    new = raw_listing()
    new["observed_at"] = "2026-10-10T12:00:00Z"
    new["fields"]["current_bid"]["value"] = 1300
    store.ingest(parse_import(encode(old), "json", NOW), "a", "1")
    lot = store.list("a")[0]
    store.set_decision("a", lot.source, lot.source_id, "candidate", "Manuell prüfen")
    assert len(store.export_candidates("a")) == 1
    assert store.decisions("b") == ()
    store.ingest(parse_import(encode(new), "json", NOW), "a", "2")
    assert store.decisions("a")[0]["review_required"]
    assert store.export_candidates("a") == ()
    assert len(store.history("a", lot.source, lot.source_id)) == 2
    store.ingest(parse_import(encode(old), "json", NOW), "a", "3")
    assert len(store.history("a", lot.source, lot.source_id)) == 2
    store.set_decision("a", lot.source, lot.source_id, "candidate")
    assert len(store.export_candidates("a")) == 1
    with pytest.raises(ValidationError):
        store.set_decision("b", lot.source, lot.source_id, "candidate")
    with pytest.raises(ValidationError):
        store.set_decision("a", lot.source, lot.source_id, "purchase")


def test_older_history_conflict_is_atomic(tmp_path):
    store = ListingStore(tmp_path / "scan.sqlite3")
    old, new = raw_listing(), raw_listing()
    new["observed_at"] = "2026-10-10T12:00:00Z"
    store.ingest(parse_import(encode(new), "json", NOW), "a", "new")
    store.ingest(parse_import(encode(old), "json", NOW), "a", "old")
    old["title"] = "Conflicting old snapshot"
    with pytest.raises(ValidationError):
        store.ingest(parse_import(encode(old), "json", NOW), "a", "conflict")
    lot = store.list("a")[0]
    assert len(store.history("a", lot.source, lot.source_id)) == 2


def test_legacy_migration_backup_and_restore(tmp_path):
    import sqlite3
    from scanner import restore_backup
    path = tmp_path / "legacy.sqlite3"
    raw = raw_listing()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE listings (workspace TEXT, source TEXT, source_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(workspace,source,source_id))")
        db.execute("CREATE TABLE imports (workspace TEXT, digest TEXT, PRIMARY KEY(workspace,digest))")
        db.execute("INSERT INTO listings VALUES (?,?,?,?)", ("a", raw["source"], raw["source_id"], json.dumps(raw)))
    store = ListingStore(path)
    lot = store.list("a")[0]
    assert len(store.history("a", lot.source, lot.source_id)) == 1
    backup = store.backup(tmp_path / "backup.sqlite3")
    restored = restore_backup(backup, tmp_path / "restore.sqlite3")
    assert ListingStore(restored).export_listings("a") == store.export_listings("a")
    assert restored.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        restore_backup(backup, restored)
    bad = tmp_path / "bad.sqlite3"
    bad.write_bytes(b"not a database")
    with pytest.raises(sqlite3.Error):
        restore_backup(bad, tmp_path / "must-not-exist.sqlite3")
    assert not (tmp_path / "must-not-exist.sqlite3").exists()


def test_scan_status_is_persistent_and_scoped(tmp_path):
    store = ListingStore(tmp_path / "scan.sqlite3")
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "bad.csv").write_text("bad")
    results = scan_inbox(inbox, store, "a")
    assert ListingStore(store.path).scan_status("a")[0]["results"] == results
    assert store.scan_status("b") == ()
    with pytest.raises(ValidationError):
        store.scan_status("a", 0)


def test_history_is_immutable_and_backup_rejects_snapshot_corruption(tmp_path):
    import sqlite3
    store = ListingStore(tmp_path / "scan.sqlite3")
    raw = raw_listing()
    store.ingest(parse_import(encode(raw), "json", NOW), "a", "first")
    with sqlite3.connect(store.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM observations")
        raw["title"] = "Tampered snapshot"
        db.execute("UPDATE listings SET payload=?", (json.dumps(raw),))
    with pytest.raises(ValidationError, match="historie"):
        store.backup(tmp_path / "bad-backup.sqlite3")
    assert not (tmp_path / "bad-backup.sqlite3").exists()


def test_store_rejects_symlink_and_future_schema(tmp_path):
    import sqlite3
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=99")
    with pytest.raises(ValidationError):
        ListingStore(path)
    link = tmp_path / "link.sqlite3"
    link.symlink_to(path)
    with pytest.raises(ValidationError):
        ListingStore(link)


def test_research_provenance_survives_restart_backup_and_restore(tmp_path):
    from research_import import parse_research_csv
    from test_research_import import row, encode as research_encode
    from scanner import restore_backup
    store = ListingStore(tmp_path / "scan.sqlite3")
    batch = parse_research_csv(research_encode(row()), now=NOW)
    store.ingest(batch, "a", "research")
    store.ingest(batch, "a", "research")
    assert store.import_provenance("a", "research") == batch.provenance
    assert store.import_provenance("b", "research") == ()
    assert len(store.export_provenance("a")) == 1
    backup = store.backup(tmp_path / "backup.sqlite3")
    restored = ListingStore(restore_backup(backup, tmp_path / "restore.sqlite3"))
    assert restored.import_provenance("a", "research") == batch.provenance
    lot = restored.list("a")[0]
    with pytest.raises(ValidationError):
        restored.set_decision("a", lot.source, lot.source_id, [])


def test_invalid_provenance_is_atomic(tmp_path):
    from types import SimpleNamespace
    store = ListingStore(tmp_path / "scan.sqlite3")
    batch = parse_import(encode(raw_listing()), "json", NOW)
    invalid = SimpleNamespace(listings=batch.listings, provenance=[{"bad": float('nan')}])
    with pytest.raises(ValidationError):
        store.ingest(invalid, "a", "bad")
    assert store.list("a") == ()


def test_selection_rejects_update_after_display(tmp_path):
    store = ListingStore(tmp_path / "db.sqlite3")
    raw = raw_listing()
    store.ingest(parse_import(encode(raw), "json", NOW), "internal", "a")
    displayed = store.list("internal")[0]
    raw["observed_at"] = "2026-10-10T12:00:00Z"
    store.ingest(parse_import(encode(raw), "json", NOW), "internal", "b")
    with pytest.raises(ValidationError, match="seit Anzeige geändert"):
        store.set_decision("internal", displayed.source, displayed.source_id, "candidate", expected_observed_at=displayed.observed_at)
    assert store.export_candidates("internal") == ()
