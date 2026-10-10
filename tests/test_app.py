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
