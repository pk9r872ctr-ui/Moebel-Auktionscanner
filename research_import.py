"""User-owned research CSV adapter. Proposed schema, not a provider API."""
import csv
import io
from dataclasses import dataclass
from imports import MAX_BYTES, MAX_LOTS, parse_import
from listings import FINANCIAL_FIELDS, Listing, ValidationError
import json
from math import isfinite

REQUIRED_COLUMNS = ('source', 'source_id', 'title', 'listing_url', 'observed_at', 'rights_reference')
OPTIONAL_COLUMNS = ('location', 'ends_at', 'status', 'price', 'price_kind', 'currency', 'bid_basis', 'description', 'terms_reference')
PRICE_KINDS = {'current', 'starting', 'minimum', 'hammer', 'total', 'manual', 'unknown'}

@dataclass(frozen=True)
class ResearchBatch:
    listings: tuple[Listing, ...]
    duplicates: int
    provenance: tuple[dict, ...]


def parse_research_csv(payload, mapping=None, delimiter=';', now=None):
    """Atomic validation; mapping canonical column -> uploaded column name."""
    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES:
        raise ValidationError('Import maximal 2 MiB')
    mapping = mapping or {}
    canonical = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    if not isinstance(mapping, dict) or any(not isinstance(v, str) for v in mapping.values()):
        raise ValidationError('Spaltenzuordnung muss Textnamen enthalten')
    effective = [mapping.get(c, c) for c in canonical]
    if set(mapping) - set(canonical) or len(set(effective)) != len(effective):
        raise ValidationError('Ungültige oder mehrdeutige Spaltenzuordnung')
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        raise ValidationError('Einzelnes CSV-Trennzeichen erforderlich')
    try:
        reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')), delimiter=delimiter)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or any(mapping.get(c, c) not in headers for c in REQUIRED_COLUMNS):
            raise ValidationError('Pflichtspalten fehlen oder doppelte CSV-Spalten')
        rows, provenance = [], []
        for number, original in enumerate(reader, 1):
            if number > MAX_LOTS or None in original or any(v is None for v in original.values()):
                raise ValidationError('Zeilenlimit oder fehlerhafte CSV-Zeile')
            data = {c: original.get(mapping.get(c, c), '') for c in REQUIRED_COLUMNS + OPTIONAL_COLUMNS}
            kind = data['price_kind'] or 'unknown'
            if kind not in PRICE_KINDS:
                raise ValidationError(f'Zeile {number}: Preisart unbekannt')
            currency = data['currency'] or 'UNKNOWN'
            if currency != 'EUR':
                raise ValidationError(f'Zeile {number}: EUR muss ausdrücklich bestätigt sein')
            price = None
            if data['price']:
                # No thousands-separator guessing or currency conversion.
                price = float(data['price'].replace(',', '.'))
                if price < 0 or not isfinite(price):
                    raise ValidationError(f'Zeile {number}: Preis ungültig')
            reference = data['listing_url']
            fields = {name: {'value': None, 'origin': 'unknown', 'reference': 'Nicht im Rechercheimport angegeben'} for name in FINANCIAL_FIELDS}
            if price is not None and kind in {'current', 'starting', 'minimum'}:
                fields['current_bid'] = {'value': price, 'origin': 'observed', 'reference': reference}
            elif price is not None and kind == 'manual':
                fields['current_bid'] = {'value': price, 'origin': 'manual', 'reference': reference}
            raw = {name: data[name] for name in REQUIRED_COLUMNS}
            raw.update(location=data['location'] or 'Unbekannt', ends_at=data['ends_at'] or None,
                       status=data['status'] or 'unknown', currency=currency,
                       bid_kind=kind if kind not in {'hammer', 'total'} else 'unknown',
                       bid_basis=data['bid_basis'] or 'unknown', fee_model='unknown',
                       terms_reference=data['terms_reference'] or 'Ungeklärt; losbezogene Bedingungen erforderlich', fields=fields)
            rows.append(raw)
            provenance.append({'row_number': number, 'source_key': [data['source'], data['source_id']],
                               'observed_at': data['observed_at'], 'original_row': dict(original),
                               'price': {'value': price, 'kind': kind, 'currency': currency},
                               'description': data['description'], 'mapping': dict(mapping),
                               'unknown_fields': [name for name, datum in fields.items() if datum['value'] is None]})
    except (UnicodeError, csv.Error, ValueError, OverflowError) as error:
        if isinstance(error, ValidationError): raise
        raise ValidationError('Recherche-CSV unlesbar oder Preisformat ungültig') from None
    batch = parse_import(json.dumps({'schema_version': 1, 'listings': rows}).encode(), 'json', now)
    return ResearchBatch(batch.listings, batch.duplicates, tuple(provenance))
