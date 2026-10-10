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
