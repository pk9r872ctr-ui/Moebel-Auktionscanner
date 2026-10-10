"""Bounded, atomic import of user-provided JSON/CSV. No network access."""
import csv
import io
import json
from dataclasses import dataclass
from listings import FINANCIAL_FIELDS, Listing, ValidationError, timestamp

MAX_BYTES = 2 * 1024 * 1024
MAX_LOTS = 1000
BASE_COLUMNS = [name for name in Listing.__dataclass_fields__ if name != "fields"]
CSV_COLUMNS = ["schema_version"] + BASE_COLUMNS + [
    f"{name}_{suffix}" for name in FINANCIAL_FIELDS for suffix in ("value", "origin", "reference")]


@dataclass(frozen=True)
class ImportBatch:
    listings: tuple[Listing, ...]
    duplicates: int


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValidationError("Doppelte JSON-Schlüssel")
        obj[key] = value
    return obj


def _reject_constant(_):
    raise ValidationError("Nicht-endliche JSON-Zahl")


def parse_import(payload: bytes, file_format: str, now=None) -> ImportBatch:
    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES:
        raise ValidationError("Import maximal 2 MiB")
    try:
        content = payload.decode("utf-8-sig")
        if file_format == "json":
            root = json.loads(content, object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
            if not isinstance(root, dict) or set(root) != {"schema_version", "listings"} or type(root["schema_version"]) is not int or root["schema_version"] != 1:
                raise ValidationError("JSON-Vertrag: schema_version 1 und listings erforderlich")
            rows = root["listings"]
        elif file_format == "csv":
            reader = csv.DictReader(io.StringIO(content), delimiter=";")
            if reader.fieldnames != CSV_COLUMNS:
                raise ValidationError("CSV-Kopf muss der Vorlage entsprechen; Trennzeichen ;")
            rows = []
            for row in reader:
                if len(rows) >= MAX_LOTS:
                    raise ValidationError("Maximal 1000 Lose")
                if None in row or any(v is None for v in row.values()) or row["schema_version"] != "1":
                    raise ValidationError("CSV-Zeile unvollständig oder Version ungültig")
                raw = {name: row[name] for name in BASE_COLUMNS}
                raw["ends_at"] = raw["ends_at"] or None
                raw["fields"] = {name: dict(
                    value=float(row[f"{name}_value"].replace(",", ".")) if row[f"{name}_value"] else None,
                    origin=row[f"{name}_origin"], reference=row[f"{name}_reference"])
                    for name in FINANCIAL_FIELDS}
                rows.append(raw)
        else:
            raise ValidationError("Nur JSON oder CSV unterstützt")
    except (UnicodeError, json.JSONDecodeError, csv.Error, ValueError, OverflowError, RecursionError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError("Import konnte nicht gelesen werden; UTF-8 und Format prüfen") from None
    if not isinstance(rows, list) or not rows or len(rows) > MAX_LOTS:
        raise ValidationError("1–1000 Lose erforderlich")
    selected = {}
    duplicates = 0
    for index, raw in enumerate(rows, 1):
        try:
            lot = Listing.parse(raw, now)
        except (ValidationError, TypeError) as error:
            raise ValidationError(f"Los {index}: {error}") from None
        previous = selected.get(lot.key)
        if previous:
            duplicates += 1
            old, new = timestamp(previous.observed_at, "observed_at"), timestamp(lot.observed_at, "observed_at")
            if old == new and previous != lot:
                raise ValidationError(f"Los {index}: widersprüchliche Dublette mit gleichem Zeitpunkt")
            if old >= new:
                continue
        selected[lot.key] = lot
    return ImportBatch(tuple(selected.values()), duplicates)


def csv_template():
    out = io.StringIO()
    csv.writer(out, delimiter=";").writerow(CSV_COLUMNS)
    return out.getvalue().encode("utf-8-sig")
