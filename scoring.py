"""Planning model: explicit invoice assumptions, never a tax eligibility decision."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Assumptions:
    target_margin: float = 0.35
    sale_haircut: float = 0.15
    transport: float = 250.0
    refurbishment: float = 100.0
    storage: float = 50.0
    disposal: float = 0.0
    vat_recoverable: bool = False
    sale_tax_mode: str = "unknown"
    sale_vat: float = 0.19
    item_vat_deductible: bool = False
    premium_vat_deductible: bool = False
    fixed_input_vat: float = 0.0


def _number(name, value, upper=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name}: endliche Zahl erforderlich")
    if value < 0 or (upper is not None and value > upper):
        raise ValueError(f"{name}: außerhalb des zulässigen Bereichs")


def deal_score(margin, roi, headroom, contribution):
    """Heuristic 0–100; not probability or market-price validation."""
    for value in (margin, roi, headroom, contribution):
        if not isfinite(value):
            raise ValueError("Score benötigt endliche Werte")
    clamp = lambda x: max(0, min(1, x))
    return round(35 * clamp(margin / .45) + 25 * clamp(roi)
                 + 20 * clamp(headroom) + 20 * clamp(contribution / 5000), 1)


def economics(current_bid, expected_resale_gross, buyer_premium, item_vat, premium_vat, a):
    """Bid and premium are NET; resale and fixed costs are GROSS.

    VAT rates/bases must be verified against the specific invoice. No support for
    VAT on a combined hammer+premium base, gross hammer bids or minimum fees.
    Margin taxation is intentionally blocked pending verified tax/purchase basis.
    """
    for name in ("vat_recoverable", "item_vat_deductible", "premium_vat_deductible"):
        if type(getattr(a, name)) is not bool:
            raise ValueError(f"{name}: bool erforderlich")
    for name, value in dict(bid=current_bid, resale=expected_resale_gross,
                            premium=buyer_premium, transport=a.transport,
                            refurbishment=a.refurbishment, storage=a.storage,
                            disposal=a.disposal, fixed_input_vat=a.fixed_input_vat).items():
        _number(name, value)
    for name, value in dict(item_vat=item_vat, premium_vat=premium_vat,
                            sale_vat=a.sale_vat, haircut=a.sale_haircut).items():
        _number(name, value, 1)
    _number("target_margin", a.target_margin, 1)
    if a.target_margin == 1:
        raise ValueError("Zielmarge muss kleiner als 100 % sein")
    if a.sale_tax_mode not in {"regular", "exempt", "unknown", "margin"}:
        raise ValueError("Unbekannter Steuermodus")
    fixed = a.transport + a.refurbishment + a.storage + a.disposal
    if a.fixed_input_vat > fixed:
        raise ValueError("Vorsteuer darf Brutto-Nebenkosten nicht überschreiten")
    if a.sale_tax_mode == "exempt" and a.vat_recoverable:
        raise ValueError("Steuerfreies Szenario mit Vorsteuerabzug ungeklärt")
    premium = current_bid * buyer_premium
    item_tax = current_bid * item_vat
    premium_tax = premium * premium_vat
    recoverable = a.vat_recoverable and a.sale_tax_mode == "regular"
    input_vat = ((item_tax if a.item_vat_deductible else 0)
                 + (premium_tax if a.premium_vat_deductible else 0)
                 + a.fixed_input_vat) if recoverable else 0
    cash = current_bid + premium + item_tax + premium_tax + fixed
    safe_gross = expected_resale_gross * (1 - a.sale_haircut)
    result = dict(cash_required=cash, input_vat=input_vat,
                  landed_cost=cash - input_vat, safe_resale_gross=safe_gross,
                  status="ok", warnings=[])
    if a.sale_tax_mode in {"unknown", "margin"}:
        result.update(status="unresolved", warnings=[
            "Steuerbehandlung ungeklärt; keine Gewinn-, Score- oder Gebotsempfehlung."
            if a.sale_tax_mode == "unknown" else
            "Differenzbesteuerung: Berechtigung und steuerlicher Einkaufspreis prüfen; Berechnung gesperrt."],
            output_vat=None, safe_resale=None, contribution=None,
            margin=None, roi=None, max_bid=None, score=None, target_feasible=None)
        return result
    output_vat = safe_gross * a.sale_vat / (1 + a.sale_vat) if a.sale_tax_mode == "regular" else 0
    revenue = safe_gross - output_vat
    contribution = revenue - result["landed_cost"]
    margin = contribution / revenue if revenue else 0
    roi = contribution / result["landed_cost"] if result["landed_cost"] else 0
    factor = 1 + buyer_premium
    factor += item_vat if not (recoverable and a.item_vat_deductible) else 0
    factor += buyer_premium * premium_vat if not (recoverable and a.premium_vat_deductible) else 0
    fixed_net = fixed - (a.fixed_input_vat if recoverable else 0)
    ceiling = revenue * (1 - a.target_margin) - fixed_net
    max_bid = max(0, ceiling / factor)
    feasible = revenue > 0 and ceiling >= 0
    headroom = (max_bid - current_bid) / max(max_bid, 1)
    result.update(output_vat=output_vat, safe_resale=revenue,
                  contribution=contribution, margin=margin, roi=roi,
                  max_bid=max_bid, target_feasible=feasible,
                  score=deal_score(margin, roi, headroom, contribution) if feasible else 0)
    return result
