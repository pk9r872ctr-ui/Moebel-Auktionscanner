from dataclasses import dataclass

@dataclass
class Assumptions:
    target_margin: float = 0.35
    sale_haircut: float = 0.15
    transport: float = 250.0
    refurbishment: float = 100.0
    storage: float = 50.0
    disposal: float = 0.0
    vat_recoverable: bool = True

def economics(current_bid, expected_resale_gross, buyer_premium, item_vat, premium_vat, a: Assumptions):
    premium = current_bid * buyer_premium
    tax_cost = 0 if a.vat_recoverable else current_bid * item_vat + premium * premium_vat
    landed = current_bid + premium + tax_cost + a.transport + a.refurbishment + a.storage + a.disposal
    safe_resale = expected_resale_gross * (1 - a.sale_haircut)
    contribution = safe_resale - landed
    margin = contribution / safe_resale if safe_resale > 0 else -1
    roi = contribution / landed if landed > 0 else 0
    fixed = a.transport + a.refurbishment + a.storage + a.disposal
    ceiling = safe_resale * (1 - a.target_margin) - fixed
    tax_factor = 0 if a.vat_recoverable else item_vat + buyer_premium * premium_vat
    max_bid = max(0, ceiling / (1 + buyer_premium + tax_factor))
    headroom = (max_bid - current_bid) / max(max_bid, 1)
    score = (35 * max(0, min(1, margin / .45))
           + 25 * max(0, min(1, roi))
           + 20 * max(0, min(1, headroom))
           + 20 * max(0, min(1, contribution / 5000)))
    return dict(landed_cost=landed, safe_resale=safe_resale, contribution=contribution,
                margin=margin, roi=roi, max_bid=max_bid, score=round(score, 1))
