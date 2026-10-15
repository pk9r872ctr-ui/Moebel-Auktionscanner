import streamlit as st
from scoring import Assumptions, economics
from sources import load_lots
from imports import parse_import, csv_template
from contracts import candidate_export
from registry import load_registry
from listings import ValidationError, timestamp
import json
from datetime import datetime, timezone, timedelta
from intelligence import analyze_listing, filter_listings, possible_duplicates
from extended_economics import ExtendedPlan, assess_extended
from research_import import parse_research_csv, parse_p0_csv, p0_import_digest
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
    st.caption(f"Konservativ geplanter Bruttoerlös: {r['safe_resale_gross']:,.2f} € · Verkaufs-USt.: {r['output_vat']:,.2f} €")
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

def show_imported_lots(listings, digest, store=None, workspace="internal", provenance=()):
    original_rows = list(provenance)
    if store:
        original_rows.extend(row for entry in store.export_provenance(workspace) for row in entry["provenance"])
    descriptions = {}
    for row in original_rows:
        if isinstance(row, dict) and isinstance(row.get("source_key"), list) and len(row["source_key"]) == 2 and all(isinstance(v, str) for v in row["source_key"]) and isinstance(row.get("description"), str):
            try:
                observed = timestamp(row.get("observed_at"), "provenance.observed_at").isoformat()
                descriptions[(tuple(row["source_key"]), observed)] = row["description"]
            except ValidationError:
                continue
    decisions = {(d["source"], d["source_id"]): d for d in store.decisions(workspace)} if store else {}
    with st.expander("Angebote suchen und filtern", expanded=True):
        search = st.text_input("Suche im Titel", key=f"search:{digest}")
        source = st.selectbox("Plattform", [""] + sorted({lot.source for lot in listings}), key=f"source:{digest}", format_func=lambda v: v or "Alle")
        category = st.selectbox("Abgeleitete Kategorie", ["", "seating", "tables", "storage", "beds"], key=f"category:{digest}", format_func=lambda v: v or "Alle")
        location = st.text_input("Standort enthält", key=f"location:{digest}")
        status = st.selectbox("Angebotsstatus", ["", "active", "ended", "unknown"], key=f"status:{digest}", format_func=lambda v: v or "Alle")
        quality = st.selectbox("Finanzdaten", ["", "complete", "incomplete"], key=f"quality:{digest}", format_func=lambda v: {"": "Alle", "complete": "Alle Werte vorhanden (nicht automatisch verifiziert)", "incomplete": "Unvollständig"}[v])
        criteria = dict(search=search, source=source, category=category, location=location, status=status, quality=quality)
        if st.checkbox("Preisbereich anwenden (unbekannte Preise ausgeschlossen)", key=f"prices:{digest}"):
            criteria["min_price"] = st.number_input("Preis ab €", min_value=0.0, key=f"min:{digest}")
            criteria["max_price"] = st.number_input("Preis bis €", min_value=0.0, value=10000.0, key=f"max:{digest}")
        if st.checkbox("Nur zukünftig endende Angebote", key=f"upcoming:{digest}"):
            criteria["upcoming"] = True
        if st.checkbox("Auktionsende innerhalb 7 Tagen", key=f"week:{digest}"):
            criteria["ends_before"] = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        decision_filter = st.selectbox("Manuelle Auswahl", ["", "watchlist", "candidate", "rejected", "unreviewed"], key=f"decisionfilter:{digest}", format_func=lambda v: v or "Alle") if store else ""
    matches = filter_listings(listings, criteria)
    if decision_filter:
        matches = [lot for lot in matches if decisions.get(lot.key, {}).get("decision", "unreviewed") == decision_filter]
    st.caption(f"{len(matches)} von {len(listings)} Angeboten · Preise behalten ihre jeweilige Gebotsart und Basis.")
    duplicates = possible_duplicates(listings)
    if duplicates:
        st.warning(f"{len(duplicates)} mögliche plattformübergreifende Dubletten: nur Prüfhinweise, keine Zusammenführung.")
        with st.expander("Dublettenhinweise"):
            st.json(duplicates)
    for lot in matches:
        p0_rows = [row for row in original_rows if row.get("p0_research") is True and row.get("source_key") == list(lot.key) and row.get("observed_at") == lot.observed_at]
        with st.container(border=True):
            st.subheader(lot.title)
            st.text(f"NUTZERIMPORT · {lot.source} / {lot.source_id} · {lot.location}")
            kind = {"current": "Aktuelles Gebot", "starting": "Startpreis", "minimum": "Mindestpreis", "manual": "Manueller Plan-Zuschlag", "unknown": "Ungeklärt"}[lot.bid_kind]
            basis = {"net": "Netto", "gross": "Brutto", "unknown": "Ungeklärt"}[lot.bid_basis]
            fee = {"net_hammer_plus_net_premium": "Netto-Zuschlag + Netto-Aufgeld", "other": "Nicht unterstützte Basis", "unknown": "Ungeklärt"}[lot.fee_model]
            st.text(f"{kind} · {basis} · {lot.currency} · Gebührenbasis: {fee}")
            st.text(f"Erfasst (Zeitart siehe Provenienz): {lot.observed_at} · Ende: {lot.ends_at or 'ungeklärt'} · Status: {lot.status}")
            st.link_button("Originalangebot öffnen", lot.listing_url)
            if p0_rows:
                st.warning("GESPERRTER RECHERCHEHINWEIS · keine Kaufempfehlung")
                for row in p0_rows:
                    st.write(f"Historischer Betrag: {row['price']['value']:,.2f} € · Preisart: {row['price']['kind']} · Nutzerbestätigung separat")
                    for issue in row["review_issues"]:
                        st.caption(issue)
                with st.expander("P0: Originaldaten, Nutzerbestätigung und Evidenz"):
                    st.json(p0_rows)
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
            matching_description = descriptions.get((lot.key, lot.observed_at), "")
            analysis = analyze_listing(lot, matching_description)
            with st.expander("Abgeleitete Möbelmerkmale und Datenqualität"):
                st.caption("Textregeln liefern Prüfhinweise; Originaldaten werden nicht überschrieben. Modell und nicht ausdrücklich genannte Stückzahlen bleiben unbekannt.")
                st.json(analysis)
            if store:
                current_decision = decisions.get(lot.key, {})
                if current_decision.get("review_required"):
                    st.warning("Angebot geändert: vorherige Entscheidung erneut prüfen. Kandidatenexport bis dahin gesperrt.")
                with st.expander("Merkliste und manuelle Entscheidung"):
                    options = ["unreviewed", "watchlist", "rejected"] if p0_rows else ["unreviewed", "watchlist", "candidate", "rejected"]
                    decision = st.selectbox("Entscheidung", options, index=options.index(current_decision.get("decision", "unreviewed")) if current_decision.get("decision", "unreviewed") in options else 0, key=f"decision:{digest}:{lot.key}")
                    note = st.text_input("Prüfnotiz (keine Buchhaltung)", value=current_decision.get("note", ""), max_chars=2000, key=f"note:{digest}:{lot.key}")
                    st.caption("Einkaufskandidat bedeutet manuelle Auswahl, keinen Nachweis von Rentabilität und keine Kaufausführung.")
                    if st.button("Entscheidung für diesen Stand speichern", key=f"save:{digest}:{lot.key}"):
                        store.set_decision(workspace, lot.source, lot.source_id, decision, note, expected_observed_at=lot.observed_at)
                        st.success("Entscheidung gespeichert")
                    st.caption(f"Beobachtungshistorie: {len(store.history(workspace, lot.source, lot.source_id))} Stände")
            reviewed = st.checkbox("Kosten, Gebührenbasis und Verkaufsschätzung für dieses Los geprüft",
                                   key=f"review:{digest}:{lot.source}:{lot.source_id}", disabled=bool(p0_rows))
            plan = None
            with st.expander("Vollkostenplan für dieses Los"):
                st.caption("Zusätzliche Bruttokosten neben den importierten Loskosten. Unbekannt bleibt leer; auch 0 muss ausdrücklich eingetragen werden. Keine Plattformgebühren werden aus dem Quellenatlas übernommen.")
                labels = {
                    "pickup": "Zusätzliche Abholung €", "dismantling": "Demontage €", "loading": "Verladung €",
                    "sales_fees": "Verkaufsgebühren brutto €", "fixed_fees": "Zusätzliche feste Kaufgebühren brutto €",
                    "financing_cost": "Finanzierungs-/Kapitalbindungskosten €", "input_vat_extra": "Bestätigte Vorsteuer in Zusatzkosten €",
                    "expected_reject_fraction": "Ausschussanteil 0–1", "resale_days": "Geplante Verkaufsdauer Tage",
                    "resale_low_gross": "Verkaufsspanne gesamt brutto: Untergrenze €", "resale_high_gross": "Verkaufsspanne gesamt brutto: Obergrenze €",
                    "target_profit": "Zieldeckungsbeitrag €", "available_cash": "Verfügbare Bruttoliquidität €"}
                values = {name: st.number_input(label, min_value=0.0, value=None, key=f"plan:{digest}:{lot.key}:{name}") for name, label in labels.items()}
                purchase_mode = st.selectbox("Einkaufssteuer laut Los-/Rechnungsbeleg", ["unknown", "regular", "no_vat_shown", "margin_explicit"], key=f"tax:{digest}:{lot.key}")
                reference = st.text_input("Planbelege und Schätzmethode", max_chars=2000, key=f"ref:{digest}:{lot.key}")
                try:
                    plan = ExtendedPlan(**values, purchase_tax_mode=purchase_mode, origin="manual", reference=reference)
                except ValueError as error:
                    st.error(str(error))
            assessed = assess_extended(lot, a, plan, review_confirmed=reviewed)
            st.caption(f"Technische Finanzvollständigkeit: {assessed['technical_priority']}/100 · keine wirtschaftliche Bewertung")
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
    st.caption("Kein Live-Abruf. Nur rechtmäßig nutzbare Daten hochladen; Herkunft wird dokumentiert, nicht unabhängig verifiziert. Upload bleibt in dieser Sitzung, außer bei ausdrücklichem Speichern in konfigurierter privater Datenbank.")
    st.download_button("Leere CSV-Vorlage", csv_template(), "auktionen-v1.csv", "text/csv")
    permitted = st.checkbox("Nutzungsrechte für den internen Datenimport geprüft", key="import_rights")
    import_format = st.selectbox("Importvertrag", ["Standard v1 CSV/JSON", "Recherche-CSV (vorgeschlagener Vertrag)", "P0: historische deutsche Recherche-CSV"])
    uploaded = st.file_uploader("CSV (; getrennt) oder JSON · maximal 2 MiB", type=["csv", "json"])
    p0_evidence = None
    p0_confirmation = None
    if import_format.startswith("P0:"):
        st.caption("P0-Kernplattformen: RESTLOS, Hämmerle, Proventura, NetBid, Zoll-Auktion. Alle 21 Quellen bleiben erhalten.")
        p0_evidence = st.file_uploader("P0-Evidenzregister (bereitgestellte CSV oder JSON, optional)", type=["csv", "json"], key="p0_evidence")
        if st.checkbox("Nutzerbestätigung aus V04: Beträge dieser Recherche sind Zuschlagspreise", key="p0_hammer"):
            p0_confirmation = "MASTER V04: Nutzer bestätigt Zuschlagspreise; keine unabhängige Plattformverifikation"
        if uploaded is not None:
            st.download_button("P0-Evidenzvorlage für diese CSV", json.dumps({"schema_version":1,"csv_sha256":hashlib.sha256(uploaded.getvalue()).hexdigest(),"entries":[]}, indent=2), "p0-evidence-template.json", "application/json")
    if uploaded is not None and (permitted or import_format.startswith("P0:")):
        payload = uploaded.getvalue()
        try:
            if import_format.startswith("P0:"):
                batch = parse_p0_csv(payload, p0_evidence.getvalue() if p0_evidence else None, hammer_confirmation=p0_confirmation)
                documented = sum(bool(row["evidence"] and row["evidence"]["rights_status"] == "documented") for row in batch.provenance)
                st.info(f"P0: {documented} Zeilen mit deklariertem Rechtsbeleg. Prüfung des Belegs bleibt erforderlich; fehlende Evidenz sperrt Bewertungen.")
            elif import_format.startswith("Recherche"):
                batch = parse_research_csv(payload)
                with st.expander("Unveränderte Recherchefelder und Preisarten"):
                    st.json(batch.provenance)
            else:
                batch = parse_import(payload, uploaded.name.rsplit(".", 1)[-1].lower())
            st.success(f"{len(batch.listings)} Angebote · {batch.duplicates} Dubletten zusammengeführt")
            digest = p0_import_digest(payload, p0_evidence.getvalue() if p0_evidence else None, p0_confirmation) if import_format.startswith("P0:") else hashlib.sha256(payload).hexdigest()
            if os.environ.get("SCANNER_DATABASE") and st.button("Geprüften Import dauerhaft speichern", key="persist_upload"):
                ListingStore(os.environ["SCANNER_DATABASE"]).ingest(batch, os.environ.get("SCANNER_WORKSPACE", "internal"), digest)
                st.success("Import atomar gespeichert; unten im Scanner-Speicher verfügbar.")
            show_imported_lots(batch.listings, digest, provenance=getattr(batch, "provenance", ()))
        except ValidationError as error:
            st.error(str(error))
        except (OSError, sqlite3.Error):
            st.error("Privater Speicher nicht verfügbar. Import wurde nicht als gespeichert bestätigt.")
    elif uploaded is not None:
        st.warning("Vor dem Import Nutzungsrechte prüfen.")
    database = os.environ.get("SCANNER_DATABASE")
    if database:
        st.subheader("Angebote aus dem Datei-Scanner")
        st.button("Scanner-Daten aktualisieren")
        try:
            # Workspace is server configuration, never an untrusted UI parameter.
            store = ListingStore(database)
            workspace = os.environ.get("SCANNER_WORKSPACE", "internal")
            listings = store.list(workspace)
            with st.expander("Datei-Scannerstatus und private Exporte"):
                runs = store.scan_status(workspace)
                if runs:
                    st.json(runs)
                else:
                    st.info("Noch kein protokollierter Scannerlauf. Ein Speicher allein belegt keinen laufenden Worker.")
                st.download_button("Unveränderte Recherche-Provenienz", json.dumps({"schema_version": 1, "imports": store.export_provenance(workspace)}, ensure_ascii=False), "recherche-provenienz-v1.json", "application/json")
                st.download_button("Aktuelle Angebotsstände im v1-Importformat", json.dumps({"schema_version": 1, "listings": store.export_listings(workspace)}, ensure_ascii=False), "angebote-v1.json", "application/json")
                st.download_button("Manuell gewählte aktuelle Einkaufskandidaten", json.dumps(candidate_export(store, workspace), ensure_ascii=False), "kandidaten-v1.json", "application/json")
            if not listings:
                st.info("Noch keine Angebote im Scanner-Speicher.")
            else:
                digest = hashlib.sha256(repr([lot.to_dict() for lot in listings]).encode()).hexdigest()
                show_imported_lots(listings, digest, store, workspace)
        except (OSError, sqlite3.Error, ValidationError):
            st.error("Scanner-Speicher nicht verfügbar oder ungültig.")


st.subheader("Basisrechnung manuell prüfen")
st.info("Diese Basisrechnung erfasst nicht alle Vollkosten. Für importierte Einkaufskandidaten den losbezogenen Vollkostenplan verwenden.")
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

with st.expander("Beschaffungsatlas und geprüfte Quellenzugänge"):
    st.caption("21 Quellen; Atlasangaben sind keine losbezogenen Kalkulationsregeln. Kein freigegebener Live-Connector.")
    st.json(load_registry())
