"""All fixtures are fabricated test data, never real listings."""
from copy import deepcopy
from datetime import datetime, timezone
import csv
import io
import json
import pytest
from imports import parse_import, csv_template, CSV_COLUMNS, MAX_BYTES
from listings import Listing, ValidationError, FINANCIAL_FIELDS

NOW = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)


def raw_listing():
    values = [1000, 2380, .2, .19, .19, 100, 0, 0, 0]
    return dict(source="test-source", source_id="test-1", title="TEST ONLY: Büromöbel",
                location="Teststadt", listing_url="https://example.org/lot/test-1",
                observed_at="2026-10-10T11:00:00Z", ends_at="2026-10-11T12:00:00Z",
                status="active", bid_basis="net", currency="EUR", bid_kind="current",
                fee_model="net_hammer_plus_net_premium", terms_reference="Testbedingungen (fiktiv)",
                rights_reference="Fiktive Testdaten – eigene Rechte",
                fields={name: dict(value=value, origin="estimated" if name in
                        {"expected_resale_gross", "transport"} else "observed", reference="Fiktiver Testbeleg")
                        for name, value in zip(FINANCIAL_FIELDS, values)})


def encode(*rows):
    return json.dumps(dict(schema_version=1, listings=list(rows))).encode()


def test_json_normalization():
    lot = parse_import(encode(raw_listing()), "json", NOW).listings[0]
    assert lot.key == ("test-source", "test-1")
    assert lot.observed_at == "2026-10-10T11:00:00+00:00"
    assert lot.fields["expected_resale_gross"].origin == "estimated"
    assert Listing.parse(lot.to_dict(), NOW) == lot


def test_csv_decimal_comma_and_unknown():
    raw = raw_listing()
    flat = dict(schema_version="1", **{k: v for k, v in raw.items() if k != "fields"})
    for name, datum in raw["fields"].items():
        for suffix, value in datum.items():
            flat[f"{name}_{suffix}"] = str(value).replace(".", ",") if suffix == "value" else value
    flat.update(transport_value="", transport_origin="unknown", transport_reference="Noch prüfen")
    out = io.StringIO()
    writer = csv.DictWriter(out, CSV_COLUMNS, delimiter=";")
    writer.writeheader()
    writer.writerow(flat)
    lot = parse_import(out.getvalue().encode("utf-8-sig"), "csv", NOW).listings[0]
    assert lot.fields["buyer_premium"].value == .2
    assert lot.fields["transport"].value is None
    assert csv_template().decode("utf-8-sig").startswith("schema_version;source;")


def test_duplicates_newest_and_conflict():
    old, new = raw_listing(), raw_listing()
    new["observed_at"] = "2026-10-10T12:00:00Z"
    new["fields"]["current_bid"]["value"] = 1200
    batch = parse_import(encode(new, old, new), "json", NOW)
    assert batch.duplicates == 2
    assert batch.listings[0].fields["current_bid"].value == 1200
    conflict = deepcopy(new)
    conflict["title"] = "conflict"
    with pytest.raises(ValidationError, match="widersprüchliche"):
        parse_import(encode(new, conflict), "json", NOW)


@pytest.mark.parametrize("field,value", [
    ("source_id", "../secret"), ("listing_url", "javascript:alert(1)"),
    ("listing_url", "https://user:pass@example.org/"),
    ("listing_url", "https://127.0.0.1/"), ("listing_url", "https://[::1]/"),
    ("listing_url", "https://localhost/"), ("listing_url", "https://example.org:8080/"),
    ("observed_at", "2026-10-10T11:00:00"), ("observed_at", "2027-01-01T00:00:00Z"),
    ("currency", "USD"), ("bid_kind", "bad"), ("fee_model", "bad"), ("status", "fake"), ("bid_basis", "maybe"), ("title", "bad\x00text"),
    ("rights_reference", ""), ("ends_at", "yesterday"),
])
def test_invalid_metadata(field, value):
    raw = raw_listing()
    raw[field] = value
    with pytest.raises(ValidationError):
        parse_import(encode(raw), "json", NOW)


@pytest.mark.parametrize("value,origin", [(None, "observed"), (1, "unknown"),
    (-1, "observed"), (True, "manual"), (float("inf"), "manual"),
    (float("nan"), "manual"), (1, "bad"), (1e20, "observed"), (1, [])])
def test_invalid_financial_values(value, origin):
    raw = raw_listing()
    raw["fields"]["transport"].update(value=value, origin=origin)
    with pytest.raises(ValidationError):
        parse_import(encode(raw), "json", NOW)


@pytest.mark.parametrize("payload,fmt", [(b"{bad", "json"), (b"\xff", "json"),
    (b"{}", "json"), (b'{"schema_version":1,"schema_version":1,"listings":[]}', "json"),
    (b"" , "csv"), (b"x" * (MAX_BYTES + 1), "json"), (b"", "xml"),
    (b"[" * 1500, "json")])
def test_bad_files(payload, fmt):
    with pytest.raises(ValidationError):
        parse_import(payload, fmt, NOW)


def test_atomic_validation_and_limits():
    good, bad = raw_listing(), raw_listing()
    bad["fields"].pop("transport")
    with pytest.raises(ValidationError, match="Los 2"):
        parse_import(encode(good, bad), "json", NOW)
    with pytest.raises(ValidationError):
        parse_import(encode(*[good] * 1001), "json", NOW)
    good["fields"]["item_vat"]["value"] = 19
    with pytest.raises(ValidationError):
        parse_import(encode(good), "json", NOW)
