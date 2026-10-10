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
