"""Explicit full-cost scenarios; no market valuation or tax eligibility inference."""
from dataclasses import asdict, dataclass
from math import isfinite
from assessment import assess_listing
from scoring import deal_score


@dataclass(frozen=True)
class ExtendedPlan:
    # All additional amounts are gross, incremental to the listing's costs.
    pickup: float | None = None
    dismantling: float | None = None
    loading: float | None = None
    sales_fees: float | None = None
    fixed_fees: float | None = None
    financing_cost: float | None = None
    input_vat_extra: float | None = None
    expected_reject_fraction: float | None = None
    resale_days: float | None = None
    resale_low_gross: float | None = None
    resale_high_gross: float | None = None
    target_profit: float | None = None
    available_cash: float | None = None
    purchase_tax_mode: str = "unknown"
    origin: str = "unknown"
    reference: str = ""

    def __post_init__(self):
        for name, value in asdict(self).items():
            if name in {"purchase_tax_mode", "origin", "reference"} or value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0 or value > 1_000_000_000:
                raise ValueError(f"{name}: endliche nichtnegative Zahl bis 1 Milliarde erforderlich")
        if self.expected_reject_fraction is not None and self.expected_reject_fraction > 1:
            raise ValueError("expected_reject_fraction: Anteil 0–1 erforderlich")
        if self.resale_low_gross is not None and self.resale_high_gross is not None and self.resale_low_gross > self.resale_high_gross:
            raise ValueError("Verkaufsspanne: Untergrenze größer als Obergrenze")
        if self.purchase_tax_mode not in {"regular", "no_vat_shown", "margin_explicit", "unknown"}:
            raise ValueError("Unbekannte Einkaufssteuerkonstellation")
        if self.origin not in {"manual", "estimated", "unknown"}:
            raise ValueError("Planherkunft muss manual, estimated oder unknown sein")
        if not isinstance(self.reference, str) or len(self.reference) > 2000:
            raise ValueError("Planreferenz ungültig")
        amounts = (self.pickup, self.dismantling, self.loading, self.sales_fees, self.fixed_fees, self.financing_cost)
        if all(v is not None for v in amounts) and self.input_vat_extra is not None and self.input_vat_extra > sum(amounts):
            raise ValueError("Zusätzliche Vorsteuer übersteigt zusätzliche Bruttokosten")


def assess_extended(listing, assumptions, plan, review_confirmed=False, now=None):
    """Return a conservative scenario with gates, never an autonomous buy instruction.

    Low/high resale refer to the complete lot before rejects and haircut. Sales
    fees are costs: output VAT is calculated from revenue BEFORE those fees.
    VAT eligibility remains explicitly supplied by the user, never inferred.
    """
    base = assess_listing(listing, assumptions, review_confirmed=review_confirmed, now=now)
    blockers = list(base["blockers"])
    technical = round(100 * sum(d.value is not None for d in listing.fields.values()) / len(listing.fields), 1)
    result = {"status": "blocked", "blockers": blockers, "economics": None,
              "technical_priority": technical, "inputs": {"listing": listing.to_dict(), "assumptions": asdict(assumptions), "plan": None}}
    if isinstance(plan, dict):
        try:
            plan = ExtendedPlan(**plan)
        except (ValueError, TypeError) as exc:
            blockers.append(str(exc))
            return result
    if not isinstance(plan, ExtendedPlan):
        blockers.append("Vollkostenplan fehlt")
        return result
    result["inputs"]["plan"] = asdict(plan)
    for name, value in asdict(plan).items():
        if value is None:
            blockers.append(f"{name}: ungeklärt; auch Nullkosten ausdrücklich bestätigen")
    if plan.origin == "unknown" or not plan.reference.strip():
        blockers.append("Planherkunft und Beleg/Methode fehlen")
    if plan.purchase_tax_mode == "unknown":
        blockers.append("Einkaufssteuerkonstellation ungeklärt")
    if plan.purchase_tax_mode in {"no_vat_shown", "margin_explicit"}:
        if listing.fields["item_vat"].value not in (None, 0) or assumptions.item_vat_deductible:
            blockers.append("Nicht ausgewiesene Zuschlags-USt darf nicht als Vorsteuer angesetzt werden")
    if plan.input_vat_extra and not (assumptions.vat_recoverable and assumptions.sale_tax_mode == "regular"):
        blockers.append("Zusätzlicher Vorsteuerabzug nicht ausdrücklich bestätigt")
    if blockers:
        return result
    # Existing listing costs remain the sole source of transport/refurbishment/etc.
    extra_gross = sum(getattr(plan, n) for n in ("pickup", "dismantling", "loading", "sales_fees", "fixed_fees", "financing_cost"))
    base_e = base["economics"]
    recoverable_extra = plan.input_vat_extra if assumptions.vat_recoverable else 0
    extra_net = extra_gross - recoverable_extra
    conservative_gross = plan.resale_low_gross * (1 - plan.expected_reject_fraction) * (1 - assumptions.sale_haircut)
    output_vat = conservative_gross * assumptions.sale_vat / (1 + assumptions.sale_vat) if assumptions.sale_tax_mode == "regular" else 0
    revenue = conservative_gross - output_vat
    cash = base_e["cash_required"] + extra_gross
    cost = base_e["landed_cost"] + extra_net
    contribution = revenue - cost
    f = listing.fields
    recoverable = assumptions.vat_recoverable and assumptions.sale_tax_mode == "regular"
    premium = f["buyer_premium"].value
    factor = 1 + premium + (0 if recoverable and assumptions.item_vat_deductible else f["item_vat"].value)
    factor += premium * (0 if recoverable and assumptions.premium_vat_deductible else f["premium_vat"].value)
    fixed_net = cost - f["current_bid"].value * factor
    ceiling = min(revenue * (1 - assumptions.target_margin), revenue - plan.target_profit) - fixed_net
    max_bid = max(0, ceiling / factor)
    cash_factor = 1 + premium + f["item_vat"].value + premium * f["premium_vat"].value
    cash_fixed = cash - f["current_bid"].value * cash_factor
    liquidity_max_bid = max(0, (plan.available_cash - cash_fixed) / cash_factor)
    max_bid = min(max_bid, liquidity_max_bid)
    margin = contribution / revenue if revenue else 0
    roi = contribution / cost if cost else 0
    feasible = revenue > 0 and ceiling >= 0 and plan.available_cash >= cash_fixed
    score = deal_score(margin, roi, (max_bid - f["current_bid"].value) / max(max_bid, 1), contribution) if feasible else 0
    result.update(status="scenario", economics={**base_e, "safe_resale_gross": conservative_gross,
        "output_vat": output_vat, "safe_resale": revenue, "cash_required": cash,
        "input_vat": base_e["input_vat"] + recoverable_extra, "landed_cost": cost,
        "contribution": contribution, "margin": margin, "roi": roi, "max_bid": max_bid,
        "score": score, "target_feasible": feasible, "additional_cost_gross": extra_gross,
        "liquidity_sufficient": plan.available_cash >= cash,
        "current_bid_meets_targets": feasible and f["current_bid"].value <= max_bid,
        "resale_days": plan.resale_days,
        "price_range_gross": [plan.resale_low_gross, plan.resale_high_gross],
        "warnings": ["Konservatives Planungsszenario; keine belegte Marktbewertung oder Kaufanweisung.",
                     "Verkaufsdauer ist dokumentiert; Finanzierungskosten müssen ausdrücklich geplant sein."]})
    return result
