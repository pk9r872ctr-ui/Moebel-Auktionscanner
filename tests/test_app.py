from pathlib import Path
from streamlit.testing.v1 import AppTest
from sources import load_lots


def test_data_separation():
    assert all(lot.is_demo for lot in load_lots())
    assert load_lots("live") == ()


def test_dashboard_modes_and_manual_calculation():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    assert any("ungeklärt" in w.value.lower() for w in app.warning)
    app.selectbox[0].set_value("regular").run()
    assert not app.exception
    assert any("Maximaler Netto-Zuschlag" in m.value for m in app.markdown)
    app.radio[0].set_value("live").run()
    assert not app.exception
    assert any("Keine echte Quelle" in i.value for i in app.info)
    app.checkbox[-1].check()
    app.button[0].click().run()
    assert not app.exception
    assert any("Deckungsbeitrag" in m.value for m in app.markdown)


def test_margin_tax_and_invalid_cost_show_warning_not_crash():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.selectbox[0].set_value("margin").run()
    assert not app.exception
    assert any("Differenzbesteuerung" in w.value for w in app.warning)
    app.selectbox[0].set_value("regular").run()
    app.checkbox[0].check().run()
    app.number_input[5].set_value(1000).run()
    assert not app.exception
    assert any("Vorsteuer" in e.value for e in app.error)


def test_import_mode_is_separate_and_has_template():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.radio[0].set_value("import").run()
    assert not app.exception
    assert any("Nutzerimport echter Angebote" in h.value for h in app.subheader)
    assert not any("Fiktiver Netto-Zuschlag" in m.value for m in app.markdown)
    assert not any("Keine echte Quelle" in i.value for i in app.info)


def test_worker_store_visible_without_demo_fallback(tmp_path, monkeypatch):
    from scanner import ListingStore
    from imports import parse_import
    from test_imports import raw_listing, encode, NOW
    store = ListingStore(tmp_path / "scanner.sqlite3")
    store.ingest(parse_import(encode(raw_listing()), "json", NOW), "internal", "test")
    monkeypatch.setenv("SCANNER_DATABASE", store.path)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.radio[0].set_value("import").run()
    assert not app.exception
    assert any("TEST ONLY" in h.value for h in app.subheader)
    assert any("Keine belastbare Empfehlung" in w.value for w in app.warning)
    assert not any("Fiktiver Netto-Zuschlag" in m.value for m in app.markdown)


def test_persisted_watchlist_and_filters(tmp_path, monkeypatch):
    from scanner import ListingStore
    from imports import parse_import
    from test_imports import raw_listing, encode, NOW
    store = ListingStore(tmp_path / "scanner.sqlite3")
    store.ingest(parse_import(encode(raw_listing()), "json", NOW), "internal", "test")
    monkeypatch.setenv("SCANNER_DATABASE", store.path)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.radio[0].set_value("import").run()
    assert not app.exception
    decision = next(s for s in app.selectbox if s.label == "Entscheidung")
    decision.set_value("watchlist").run()
    next(b for b in app.button if b.label == "Entscheidung für diesen Stand speichern").click().run()
    assert not app.exception
    assert store.decisions("internal")[0]["decision"] == "watchlist"
    assert any("Keine belastbare Empfehlung" in w.value for w in app.warning)
    next(t for t in app.text_input if t.label == "Suche im Titel").set_value("no matching listing").run()
    assert not app.exception
    assert not any("TEST ONLY" in h.value for h in app.subheader)


def test_full_cost_ui_stays_blocked_until_explicit_complete_plan(tmp_path, monkeypatch):
    from scanner import ListingStore
    from imports import parse_import
    from test_imports import raw_listing, encode, NOW
    store = ListingStore(tmp_path / "scanner.sqlite3")
    from datetime import datetime, timezone, timedelta
    raw = raw_listing()
    raw["observed_at"] = datetime.now(timezone.utc).isoformat()
    raw["ends_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    store.ingest(parse_import(encode(raw), "json"), "internal", "test")
    monkeypatch.setenv("SCANNER_DATABASE", store.path)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.radio[0].set_value("import").run()
    app.selectbox[0].set_value("regular").run()
    next(c for c in app.checkbox if c.label == "Kosten, Gebührenbasis und Verkaufsschätzung für dieses Los geprüft").check().run()
    assert any("ungeklärt" in w.value for w in app.warning)
    # Zero additional costs require deliberate input; uncertain resale/liquidity explicit.
    for control in app.number_input:
        if control.key and str(control.key).startswith("plan:"):
            value = 3000.0 if "resale_" in str(control.key) and "days" not in str(control.key) else 0.0
            if "available_cash" in str(control.key):
                value = 10000.0
            if "resale_days" in str(control.key):
                value = 30.0
            control.set_value(value)
    next(s for s in app.selectbox if s.label == "Einkaufssteuer laut Los-/Rechnungsbeleg").set_value("regular")
    next(t for t in app.text_input if t.label == "Planbelege und Schätzmethode").set_value("TEST ONLY synthetic manual plan, no market validation")
    for control in app.number_input:
        if control.key and (str(control.key).startswith("price-risk:") or str(control.key).startswith("demand-risk:")):
            control.set_value(0.0)
    app.run()
    assert not app.exception
    assert any("Deckungsbeitrag" in m.value for m in app.markdown)
