from dataclasses import replace
import math
import pytest
from scoring import Assumptions, economics, deal_score

BASE = Assumptions(sale_haircut=0, transport=100, refurbishment=0,
                   storage=0, sale_tax_mode="regular")


def calc(a=BASE, bid=1000, resale=2380):
    return economics(bid, resale, .2, .19, .19, a)


def test_gross_net_and_cash_without_deduction():
    r = calc()
    assert r["cash_required"] == pytest.approx(1528)
    assert r["landed_cost"] == pytest.approx(1528)
    assert r["output_vat"] == pytest.approx(380)
    assert r["safe_resale"] == pytest.approx(2000)
    assert r["contribution"] == pytest.approx(472)


def test_invoice_specific_input_vat():
    a = replace(BASE, vat_recoverable=True, item_vat_deductible=True,
                premium_vat_deductible=True, fixed_input_vat=10)
    r = calc(a)
    assert r["cash_required"] == pytest.approx(1528)
    assert r["input_vat"] == pytest.approx(238)
    assert r["landed_cost"] == pytest.approx(1290)
    partial = calc(replace(a, item_vat_deductible=False))
    assert partial["input_vat"] == pytest.approx(48)


@pytest.mark.parametrize("deduct", [False, True])
@pytest.mark.parametrize("mode", ["regular", "exempt"])
def test_max_bid_hits_target(deduct, mode):
    a = replace(BASE, sale_tax_mode=mode, vat_recoverable=deduct and mode == "regular",
                item_vat_deductible=True, premium_vat_deductible=True)
    r = calc(a)
    at_ceiling = calc(a, bid=r["max_bid"])
    assert at_ceiling["margin"] == pytest.approx(a.target_margin)
    assert calc(a, bid=r["max_bid"] + 1)["margin"] < a.target_margin


def test_exempt_and_haircut():
    r = calc(replace(BASE, sale_tax_mode="exempt", sale_haircut=.5))
    assert r["safe_resale"] == 1190
    assert r["output_vat"] == 0
    assert r["input_vat"] == 0


@pytest.mark.parametrize("mode", ["unknown", "margin"])
def test_unresolved_blocks_recommendations(mode):
    r = calc(replace(BASE, sale_tax_mode=mode, vat_recoverable=True))
    assert r["status"] == "unresolved"
    assert r["input_vat"] == 0
    assert r["warnings"]
    for key in ("max_bid", "score", "contribution", "margin", "safe_resale"):
        assert r[key] is None


def test_no_revenue_and_unreachable_target():
    r = calc(resale=0)
    assert r["max_bid"] == 0
    assert not r["target_feasible"]
    assert r["score"] == 0
    assert calc(resale=100)["target_feasible"] is False


def test_free_lot_has_finite_metrics():
    r = economics(0, 1190, 0, 0, 0, replace(BASE, transport=0))
    assert r["contribution"] == pytest.approx(1000)
    assert math.isfinite(r["roi"])


@pytest.mark.parametrize("bid", [-1, float("nan"), float("inf"), True])
def test_invalid_bid(bid):
    with pytest.raises(ValueError):
        calc(bid=bid)


@pytest.mark.parametrize("change", [dict(target_margin=1), dict(sale_haircut=1.1),
    dict(fixed_input_vat=101), dict(sale_tax_mode="bad"),
    dict(sale_tax_mode="exempt", vat_recoverable=True)])
def test_invalid_assumptions(change):
    with pytest.raises(ValueError):
        calc(replace(BASE, **change))


def test_score_bounds_and_weights():
    assert deal_score(-1, -1, -1, -1) == 0
    assert deal_score(.45, 1, 1, 5000) == 100
    assert deal_score(.45, 0, 0, 0) == 35
    assert deal_score(.2, .2, .2, 1000) < deal_score(.3, .3, .3, 2000)
    with pytest.raises(ValueError):
        deal_score(float("nan"), 0, 0, 0)


def test_fixed_vat_ignored_without_entitlement():
    assert calc(replace(BASE, fixed_input_vat=10))["input_vat"] == 0


@pytest.mark.parametrize("premium,item_vat,premium_vat", [(-.1, 0, 0), (0, -.1, 0), (0, 0, 1.1)])
def test_invalid_fee_or_tax(premium, item_vat, premium_vat):
    with pytest.raises(ValueError):
        economics(100, 1000, premium, item_vat, premium_vat, BASE)


@pytest.mark.parametrize("flag", ["vat_recoverable", "item_vat_deductible", "premium_vat_deductible"])
def test_vat_flags_are_strict_booleans(flag):
    from dataclasses import replace
    with pytest.raises(ValueError, match="bool"):
        economics(1000, 2380, .2, .19, .19, replace(Assumptions(sale_tax_mode="regular"), **{flag: "false"}))
