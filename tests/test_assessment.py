from dataclasses import replace
import pytest
from assessment import assess_listing
from listings import Listing
from scoring import Assumptions
from test_imports import raw_listing, NOW

A = Assumptions(sale_tax_mode="regular", sale_haircut=0)


def test_import_economics_uses_per_lot_costs():
    lot = Listing.parse(raw_listing(), NOW)
    r = assess_listing(lot, A, review_confirmed=True, now=NOW)
    assert r["status"] == "scenario"
    assert r["economics"]["contribution"] == pytest.approx(472)
    assert assess_listing(lot, A, now=NOW)["status"] == "blocked"


@pytest.mark.parametrize("field,value", [("status", "ended"), ("status", "unknown"),
    ("ends_at", None), ("ends_at", "2026-10-09T12:00:00Z"),
    ("observed_at", "2026-10-08T12:00:00Z"), ("bid_basis", "gross"),
    ("bid_basis", "unknown"), ("bid_kind", "starting"), ("bid_kind", "minimum"),
    ("fee_model", "other"), ("fee_model", "unknown")])
def test_missing_stale_or_ended_blocks(field, value):
    raw = raw_listing()
    raw[field] = value
    result = assess_listing(Listing.parse(raw, NOW), A, review_confirmed=True, now=NOW)
    assert result["status"] == "blocked"
    assert result["economics"] is None


@pytest.mark.parametrize("field", ["transport", "expected_resale_gross", "buyer_premium", "item_vat"])
def test_unknown_blocks(field):
    raw = raw_listing()
    raw["fields"][field].update(value=None, origin="unknown")
    assert assess_listing(Listing.parse(raw, NOW), A, review_confirmed=True, now=NOW)["economics"] is None


def test_estimated_fee_and_unknown_tax_block():
    raw = raw_listing()
    raw["fields"]["buyer_premium"]["origin"] = "estimated"
    assert assess_listing(Listing.parse(raw, NOW), A, review_confirmed=True, now=NOW)["status"] == "blocked"
    lot = Listing.parse(raw_listing(), NOW)
    for mode in ("unknown", "margin"):
        assert assess_listing(lot, replace(A, sale_tax_mode=mode), review_confirmed=True, now=NOW)["status"] == "blocked"
    assert assess_listing(lot, replace(A, vat_recoverable=True, fixed_input_vat=200), review_confirmed=True, now=NOW)["status"] == "blocked"


def test_review_string_does_not_authorize_scenario():
    from imports import parse_import
    from test_imports import raw_listing, encode, NOW
    lot = parse_import(encode(raw_listing()), "json", NOW).listings[0]
    assert assess_listing(lot, Assumptions(sale_tax_mode="regular"), review_confirmed="false", now=NOW)["status"] == "blocked"
