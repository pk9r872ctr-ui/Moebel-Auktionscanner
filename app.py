import streamlit as st
from scoring import Assumptions, economics
from sources import load_lots

st.set_page_config(page_title="Möbel-Auktionsscanner", page_icon="🪑", layout="centered")
st.title("🪑 Möbel-Auktionsscanner")
st.caption("MVP · manuelle Planung · keine Gebotsabgabe")
st.warning("DEMO: Alle Lose, Preise und Gebühren sind fiktiv. Keine Live-Auktionen.")
st.markdown("""<style>@media(max-width:600px){.block-container{padding:4rem .75rem 3rem;}h1{font-size:1.65rem!important;}}</style>""", unsafe_allow_html=True)

with st.expander("Kosten und Steuerannahmen", expanded=True):
    mode = st.selectbox("Verkaufsbesteuerung", ["unknown", "regular", "exempt", "margin"],
        format_func=lambda x: {"unknown": "Ungeklärt – Empfehlungen gesperrt", "regular": "Regelbesteuerung (bestätigtes Szenario)", "exempt": "Ohne Verkaufs-USt. und Vorsteuerabzug (bestätigt)", "margin": "Differenzbesteuerung – Prüfung erforderlich"}[x])
    sale_vat = st.number_input("Verkaufs-USt. % (bei Regelbesteuerung)", 0.0, 100.0, 19.0) / 100
    target = st.slider("Zielmarge auf Erlös nach Verkaufs-USt.", .0, .9, .35, .05)
    haircut = st.slider("Sicherheitsabschlag auf Brutto-Verkaufspreis", .0, 1.0, .15, .05)
    transport = st.number_input("Transport brutto €", min_value=0.0, value=250.0)
    refurbishment = st.number_input("Aufbereitung brutto €", min_value=0.0, value=100.0)
    storage = st.number_input("Lager brutto €", min_value=0.0, value=50.0)
    disposal = st.number_input("Entsorgung brutto €", min_value=0.0, value=0.0)
    recover = st.checkbox("Vorsteuerabzugsberechtigung bestätigt", disabled=mode != "regular") and mode == "regular"
    item_deduct = st.checkbox("Waren-USt. laut Rechnung abzugsfähig", disabled=not recover)
    premium_deduct = st.checkbox("Aufgeld-USt. laut Rechnung abzugsfähig", disabled=not recover)
    fixed_vat = st.number_input("Bestätigte Vorsteuer in Brutto-Nebenkosten €", min_value=0.0, value=0.0, disabled=not recover)
    st.caption("Netto-Zuschlag + Netto-Aufgeld; USt. jeweils auf diese Basis. Abweichende Gebühren-/Steuerbasen werden nicht unterstützt. 0 % Waren-USt. begründet keine Differenzbesteuerung.")
a = Assumptions(target, haircut, transport, refurbishment, storage, disposal,
                recover, mode, sale_vat, item_deduct, premium_deduct, fixed_vat if recover else 0)


def show_result(r):
    st.write(f"**Zahlungsbedarf: {r['cash_required']:,.2f} €**")
    st.caption(f"Abziehbare Vorsteuer: {r['input_vat']:,.2f} € · Wirtschaftliche Kosten: {r['landed_cost']:,.2f} €")
    if r["status"] != "ok":
        st.warning(r["warnings"][0])
        return
    st.write(f"Erlös nach Verkaufs-USt.: {r['safe_resale']:,.2f} €")
    st.caption(f"Sicherer Bruttoerlös: {r['safe_resale_gross']:,.2f} € · Verkaufs-USt.: {r['output_vat']:,.2f} €")
    st.write(f"**Deckungsbeitrag: {r['contribution']:,.2f} € · Marge: {r['margin']:.1%}**")
    if r["target_feasible"]:
        st.write(f"**Maximaler Netto-Zuschlag: {r['max_bid']:,.2f} €** · Deal-Score: {r['score']}/100")
    else:
        st.warning("Zielmarge selbst bei 0 € Zuschlag nicht erreichbar bzw. kein Erlös.")


data_mode = st.radio("Datenmodus", ["demo", "live"], format_func=lambda x: "Fiktive Demo" if x == "demo" else "Echte Daten (noch nicht angeschlossen)")
try:
    rows = [(lot, economics(lot.current_bid, lot.expected_resale_gross,
            lot.buyer_premium, lot.item_vat, lot.premium_vat, a)) for lot in load_lots(data_mode)]
    rows.sort(key=lambda row: row[1]["score"] or 0, reverse=True)
    if not rows:
        st.info("Keine echte Quelle konfiguriert. Es werden keine Demo-Lose als echte Daten angezeigt.")
    for lot, result in rows:
        with st.container(border=True):
            st.subheader(lot.title)
            st.caption(f"DEMO · {lot.source_label} · {lot.location}")
            st.write(f"Fiktiver Netto-Zuschlag: {lot.current_bid:,.2f} €")
            with st.expander("Fiktive Gebühren und Preise"):
                st.write(f"Aufgeld netto: {lot.buyer_premium:.1%} · Waren-USt.: {lot.item_vat:.1%} · Aufgeld-USt.: {lot.premium_vat:.1%}")
                st.write(f"Geschätzter Brutto-Verkaufspreis: {lot.expected_resale_gross:,.2f} €")
            show_result(result)
except ValueError as error:
    st.error(str(error))

st.subheader("Los manuell bewerten")
st.caption("Gebühren und USt. aus den konkreten Auktionsbedingungen übernehmen. Eingaben werden nicht gespeichert.")
with st.form("manual"):
    bid = st.number_input("Netto-Zuschlag €", min_value=0.0, value=1000.0)
    resale = st.number_input("Erwarteter Brutto-Verkaufspreis €", min_value=0.0, value=5000.0)
    premium = st.number_input("Aufgeld netto %", min_value=0.0, value=0.0) / 100
    item_vat = st.number_input("USt. auf Netto-Ware %", 0.0, 100.0, 0.0) / 100
    premium_vat = st.number_input("USt. auf Netto-Aufgeld %", 0.0, 100.0, 0.0) / 100
    confirmed = st.checkbox("Gebühren und Steuerbasis anhand der Bedingungen geprüft")
    submit = st.form_submit_button("Berechnen", use_container_width=True)
if submit:
    if not confirmed:
        st.warning("Zuerst Gebühren und Steuerbasis prüfen und bestätigen.")
    else:
        try:
            show_result(economics(bid, resale, premium, item_vat, premium_vat, a))
        except ValueError as error:
            st.error(str(error))
st.caption("Score = heuristische Gewichtung von Marge, ROI, Gebotsspielraum und Deckungsbeitrag; keine Erfolgswahrscheinlichkeit. Deckungsbeitrag vor Arbeit, Ertragsteuern und weiteren nicht erfassten Kosten.")
