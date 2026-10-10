from dataclasses import replace
import pytest
from extended_economics import ExtendedPlan, assess_extended
from listings import Listing
from scoring import Assumptions
from test_imports import raw_listing, NOW

A = Assumptions(sale_tax_mode="regular", sale_haircut=0, target_margin=0)
P = ExtendedPlan(pickup=0, dismantling=0, loading=0, sales_fees=0,
    fixed_fees=0, financing_cost=0, input_vat_extra=0,
    expected_reject_fraction=0, resale_days=30, resale_low_gross=1190,
    resale_high_gross=1500, target_profit=100, available_cash=10000,
    purchase_tax_mode="regular", origin="manual", reference="Manuell geprüfter Testplan (synthetisch)")


def assess(plan=P, a=A, raw=None):
    return assess_extended(Listing.parse(raw or raw_listing(), NOW), a, plan, True, NOW)


def test_full_costs_are_incremental_not_double_counted():
    initial = assess()["economics"]
    changed = assess(replace(P, pickup=20, dismantling=30, loading=10, sales_fees=40, fixed_fees=5, financing_cost=5))["economics"]
    assert changed["cash_required"] == initial["cash_required"] + 110
    assert changed["contribution"] == initial["contribution"] - 110
    assert changed["output_vat"] == initial["output_vat"]
    assert changed["safe_resale"] == 1000


def test_absolute_profit_boundary_and_bid_increase():
    e = assess()["economics"]
    raw = raw_listing()
    raw["fields"]["current_bid"]["value"] = e["max_bid"]
    boundary = assess(raw=raw)["economics"]
    assert boundary["contribution"] == pytest.approx(P.target_profit)
    raw["fields"]["current_bid"]["value"] += 1
    assert assess(raw=raw)["economics"]["contribution"] < P.target_profit


def test_target_margin_is_also_respected():
    e = assess(a=replace(A, target_margin=.4))["economics"]
    raw = raw_listing()
    raw["fields"]["current_bid"]["value"] = e["max_bid"]
    assert assess(a=replace(A, target_margin=.4), raw=raw)["economics"]["margin"] == pytest.approx(.4)


def test_rejects_and_haircut_reduce_revenue_not_sales_fees_tax_base():
    e = assess(replace(P, expected_reject_fraction=.2, sales_fees=50), replace(A, sale_haircut=.1))["economics"]
    assert e["safe_resale"] == pytest.approx(720)
    assert e["output_vat"] == pytest.approx(136.8)


def test_liquidity_caps_max_bid_even_with_recoverable_vat():
    a = replace(A, vat_recoverable=True, item_vat_deductible=True, premium_vat_deductible=True)
    e = assess(replace(P, available_cash=300), a)["economics"]
    assert e["liquidity_sufficient"] is False
    raw = raw_listing()
    raw["fields"]["current_bid"]["value"] = e["max_bid"]
    assert assess(replace(P, available_cash=300), a, raw)["economics"]["cash_required"] == pytest.approx(300)


@pytest.mark.parametrize("field", ["pickup", "sales_fees", "input_vat_extra", "expected_reject_fraction", "resale_days", "target_profit", "available_cash"])
def test_unknown_explicitly_blocks(field):
    r = assess(replace(P, **{field: None}))
    assert r["status"] == "blocked"
    assert r["economics"] is None
    assert r["technical_priority"] == 100


@pytest.mark.parametrize("plan", [None, {}, {"bad": 1}])
def test_missing_or_invalid_plan_blocks(plan):
    assert assess(plan)["status"] == "blocked"


def test_purchase_tax_unknown_and_margin_sale_block():
    assert assess(replace(P, purchase_tax_mode="unknown"))["status"] == "blocked"
    assert assess(replace(P, purchase_tax_mode="margin_explicit"), replace(A, sale_tax_mode="margin"))["status"] == "blocked"
    raw = raw_listing()
    raw["fields"]["item_vat"]["value"] = 0
    assert assess(replace(P, purchase_tax_mode="margin_explicit"), raw=raw)["status"] == "scenario"
    assert assess(replace(P, purchase_tax_mode="no_vat_shown"), replace(A, item_vat_deductible=True), raw)["status"] == "blocked"


def test_extra_input_vat_requires_confirmation():
    plan = replace(P, loading=119, input_vat_extra=19)
    assert assess(plan)["status"] == "blocked"
    e = assess(plan, replace(A, vat_recoverable=True))["economics"]
    assert e["additional_cost_gross"] == 119
    assert e["input_vat"] == 19


@pytest.mark.parametrize("kwargs", [{"pickup": True}, {"loading": -1}, {"resale_days": float("nan")},
    {"expected_reject_fraction": 1.1}, {"resale_low_gross": 2000}, {"input_vat_extra": 1},
    {"purchase_tax_mode": "made-up"}, {"origin": "observed"}])
def test_strict_plan_validation(kwargs):
    with pytest.raises(ValueError):
        replace(P, **kwargs)


def test_dict_interface_and_review_gate():
    from dataclasses import asdict
    assert assess(asdict(P))["status"] == "scenario"
    lot = Listing.parse(raw_listing(), NOW)
    assert assess_extended(lot, A, P, now=NOW)["status"] == "blocked"
    assert assess(replace(P, reference=""))["status"] == "blocked"


def test_extreme_plan_values_rejected_before_arithmetic():
    import pytest
    with pytest.raises(ValueError):
        ExtendedPlan(resale_low_gross=1e308)
