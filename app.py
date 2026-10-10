import pandas as pd
import streamlit as st
from sources import SOURCES
from scoring import Assumptions, economics
from sample_data import LOTS

st.set_page_config(page_title="Möbel-Auktionsscanner", layout="wide")
st.title("Möbel-Auktionsscanner · MVP")
st.warning("Demonstrationsdaten und vereinfachte Steuer-/Gebührenannahmen. Keine Live-Auktionen und keine verlässliche Gewinnprognose.")

with st.sidebar:
    st.header("Annahmen")
    target_margin = st.slider("Zielmarge", 0.10, 0.70, 0.35, 0.05)
    haircut = st.slider("Sicherheitsabschlag Verkauf", 0.0, 0.50, 0.15, 0.05)
    transport = st.number_input("Transport €", 0, 5000, 250, 50)
    refurbishment = st.number_input("Aufbereitung €", 0, 5000, 100, 50)
    storage = st.number_input("Lager €", 0, 5000, 50, 25)
    vat_recoverable = st.checkbox("Vorsteuer als abzugsfähig annehmen", True)

a = Assumptions(target_margin, haircut, transport, refurbishment, storage, 0, vat_recoverable)
rows = []
for lot in LOTS:
    cfg = SOURCES[lot["source"]]
    result = economics(lot["current_bid"], lot["expected_resale"], cfg["buyer_premium"], lot["item_vat"], cfg["premium_vat"], a)
    rows.append({**lot, **result})
df = pd.DataFrame(rows).sort_values("score", ascending=False)
st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Los manuell bewerten")
with st.form("manual"):
    source = st.selectbox("Auktionsplattform", list(SOURCES))
    bid = st.number_input("Gebot €", min_value=0.0, value=1000.0)
    resale = st.number_input("Erwarteter Brutto-Verkaufserlös €", min_value=0.0, value=5000.0)
    item_vat = st.selectbox("USt. auf Ware", [0.0, 0.19], format_func=lambda x: f"{x:.0%}")
    submit = st.form_submit_button("Berechnen")
if submit:
    cfg = SOURCES[source]
    r = economics(bid, resale, cfg["buyer_premium"], item_vat, cfg["premium_vat"], a)
    st.write({k: round(v, 2) for k, v in r.items()})
