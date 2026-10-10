import streamlit as st
from scoring import Assumptions, economics
from sources import load_lots
from imports import parse_import, csv_template
from assessment import assess_listing
from listings import ValidationError
import hashlib
import os
import sqlite3
from scanner import ListingStore
from access import enforce_access

st.set_page_config(page_title="Möbel-Auktionsscanner", page_icon="🪑", layout="centered")
enforce_access()
st.title("🪑 Möbel-Auktionsscanner")
st.caption("MVP · manuelle Planung · keine Gebotsabgabe")
st.info("Interner Scanner · Demo und Nutzerimport getrennt · kein automatischer Live-Abruf")
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





FIELD_LABELS = {
    "current_bid": "Gebot / Plan-Zuschlag", "expected_resale_gross": "Geschätzter Brutto-Verkaufspreis",
    "buyer_premium": "Aufgeld", "item_vat": "Waren-USt.", "premium_vat": "Aufgeld-USt.",
    "transport": "Transport brutto", "refurbishment": "Aufbereitung brutto",
    "storage": "Lager brutto", "disposal": "Entsorgung brutto",
}
ORIGIN_LABELS = {"observed": "Beobachtet", "estimated": "Geschätzt", "manual": "Manuell eingegeben", "unknown": "Ungeklärt"}

def show_imported_lots(listings, digest):
    for lot in listings:
        with st.container(border=True):
            st.subheader(lot.title)
            st.text(f"NUTZERIMPORT · {lot.source} / {lot.source_id} · {lot.location}")
            kind = {"current": "Aktuelles Gebot", "starting": "Startpreis", "minimum": "Mindestpreis", "manual": "Manueller Plan-Zuschlag", "unknown": "Ungeklärt"}[lot.bid_kind]
            basis = {"net": "Netto", "gross": "Brutto", "unknown": "Ungeklärt"}[lot.bid_basis]
            fee = {"net_hammer_plus_net_premium": "Netto-Zuschlag + Netto-Aufgeld", "other": "Nicht unterstützte Basis", "unknown": "Ungeklärt"}[lot.fee_model]
            st.text(f"{kind} · {basis} · {lot.currency} · Gebührenbasis: {fee}")
            st.text(f"Beobachtet: {lot.observed_at} · Ende: {lot.ends_at or 'ungeklärt'} · Status: {lot.status}")
            st.link_button("Originalangebot öffnen", lot.listing_url)
            with st.expander("Beobachtungen, Schätzungen und manuelle Angaben"):
                for name, datum in lot.fields.items():
                    if datum.value is None:
                        value = "ungeklärt"
                    elif name in {"buyer_premium", "item_vat", "premium_vat"}:
                        value = f"{datum.value:.1%}"
                    else:
                        value = f"{datum.value:,.2f} €"
                    st.text(f"{FIELD_LABELS[name]}: {value} · {ORIGIN_LABELS[datum.origin]} · {datum.reference}")
                st.text(f"Gebührenbeleg: {lot.terms_reference}")
                st.text(f"Nutzungsrechte: {lot.rights_reference}")
            reviewed = st.checkbox("Kosten, Gebührenbasis und Verkaufsschätzung für dieses Los geprüft",
                                   key=f"review:{digest}:{lot.source}:{lot.source_id}")
            assessed = assess_listing(lot, a, review_confirmed=reviewed)
            if assessed["status"] == "blocked":
                st.warning("Keine belastbare Empfehlung: " + "; ".join(assessed["blockers"]))
            else:
                st.info("Manuell geprüftes Planungsszenario; Schätzungen bleiben unsicher. Keine automatische Kaufempfehlung.")
                show_result(assessed["economics"])

data_mode = st.radio("Datenmodus", ["demo", "import", "live"], format_func=lambda x: {"demo": "Fiktive Demo", "import": "Echte Daten aus Nutzerimport", "live": "Live-Zugang (gesperrt)"}[x])
if data_mode == "demo":
    st.warning("DEMO: Alle Lose, Preise und Gebühren sind fiktiv.")

try:
    rows = [(lot, economics(lot.current_bid, lot.expected_resale_gross,
            lot.buyer_premium, lot.item_vat, lot.premium_vat, a)) for lot in (load_lots(data_mode) if data_mode != "import" else ())]
    rows.sort(key=lambda row: row[1]["score"] or 0, reverse=True)
    if not rows and data_mode == "live":
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

if data_mode == "import":
    st.subheader("Nutzerimport echter Angebote")
    st.caption("Kein Live-Abruf. Nur rechtmäßig nutzbare Daten hochladen; Herkunft wird dokumentiert, nicht unabhängig verifiziert. Upload bleibt in dieser Sitzung.")
    st.download_button("Leere CSV-Vorlage", csv_template(), "auktionen-v1.csv", "text/csv")
    permitted = st.checkbox("Nutzungsrechte für den internen Datenimport geprüft", key="import_rights")
    uploaded = st.file_uploader("CSV (; getrennt) oder JSON · maximal 2 MiB", type=["csv", "json"])
    if uploaded is not None and permitted:
        payload = uploaded.getvalue()
        try:
            batch = parse_import(payload, uploaded.name.rsplit(".", 1)[-1].lower())
            st.success(f"{len(batch.listings)} Angebote · {batch.duplicates} Dubletten zusammengeführt")
            digest = hashlib.sha256(payload).hexdigest()
            show_imported_lots(batch.listings, digest)
        except ValidationError as error:
            st.error(str(error))
    elif uploaded is not None:
        st.warning("Vor dem Import Nutzungsrechte prüfen.")
    database = os.environ.get("SCANNER_DATABASE")
    if database:
        st.subheader("Angebote aus dem Datei-Scanner")
        st.button("Scanner-Daten aktualisieren")
        try:
            # Workspace is server configuration, never an untrusted UI parameter.
            listings = ListingStore(database).list(os.environ.get("SCANNER_WORKSPACE", "internal"))
            if not listings:
                st.info("Noch keine Angebote im Scanner-Speicher.")
            else:
                digest = hashlib.sha256(repr([lot.to_dict() for lot in listings]).encode()).hexdigest()
                show_imported_lots(listings, digest)
        except (OSError, sqlite3.Error, ValidationError):
            st.error("Scanner-Speicher nicht verfügbar oder ungültig.")


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
