"""Completeness/freshness gate between observed listings and planning economics."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from listings import timestamp
from scoring import economics


def assess_listing(lot, assumptions, *, review_confirmed=False, now=None):
    now = now or datetime.now(timezone.utc)
    blockers = []
    if lot.terms_reference.startswith("P0:"):
        blockers.append("Historischer P0-Recherchehinweis bleibt gesperrt")
    if type(review_confirmed) is not bool or not review_confirmed:
        blockers.append("Kosten, Gebührenbasis und Verkaufsschätzung noch nicht manuell geprüft")
    if lot.status != "active":
        blockers.append("Auktionsstatus nicht aktiv")
    if lot.ends_at is None or timestamp(lot.ends_at, "ends_at") <= now:
        blockers.append("Auktionsende fehlt oder ist überschritten")
    age = now - timestamp(lot.observed_at, "observed_at")
    if age > timedelta(hours=24) or age < timedelta(minutes=-5):
        blockers.append("Beobachtung älter als 24 Stunden oder in der Zukunft")
    if lot.bid_basis != "net":
        blockers.append("Netto-Gebotsbasis nicht bestätigt")
    if lot.fee_model != "net_hammer_plus_net_premium":
        blockers.append("Gebühren-/Steuerbasen unbekannt oder nicht unterstützt")
    if lot.bid_kind not in {"current", "manual"}:
        blockers.append("Preis ist kein aktuelles Gebot oder manuell gewählter Plan-Zuschlag")
    for name, datum in lot.fields.items():
        if datum.value is None:
            blockers.append(f"{name}: ungeklärt")
    # Fee and VAT guesses cannot become verified merely by ticking a box.
    for name in ("current_bid", "buyer_premium", "item_vat", "premium_vat"):
        if lot.fields[name].origin not in {"observed", "manual"}:
            blockers.append(f"{name}: beobachteter oder geprüfter manueller Wert erforderlich")
    if assumptions.sale_tax_mode not in {"regular", "exempt"}:
        blockers.append("Verkaufsbesteuerung ungeklärt oder Differenzbesteuerung gesperrt")
    if blockers:
        return {"status": "blocked", "blockers": blockers, "economics": None}
    f = {name: datum.value for name, datum in lot.fields.items()}
    a = replace(assumptions, **{name: f[name] for name in ("transport", "refurbishment", "storage", "disposal")})
    try:
        result = economics(f["current_bid"], f["expected_resale_gross"],
                           f["buyer_premium"], f["item_vat"], f["premium_vat"], a)
    except ValueError as error:
        return {"status": "blocked", "blockers": [str(error)], "economics": None}
    return {"status": "scenario", "blockers": [], "economics": result}
