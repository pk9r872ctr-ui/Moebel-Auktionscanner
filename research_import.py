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


# Existing v1 Listing + provenance sidecar; no new database or data-contract version.
P0_CORE_SOURCES = ('restlos', 'haemmerle', 'proventura', 'netbid', 'zoll-auktion')
P0_COLUMNS = ('quelle', 'auktions_id', 'titel', 'standort', 'angezeigter_betrag_eur',
              'auktionsende_datum', 'status_am_2026_10_10', 'original_url', 'datenhinweis')
P0_EVIDENCE_FIELDS = {'source', 'source_id', 'rights_status', 'rights_scope', 'rights_reference',
                      'reviewed_by', 'reviewed_at', 'source_observed_at', 'time_reference',
                      'hammer_verification', 'hammer_reference'}


def p0_import_digest(payload, evidence=None, hammer_confirmation=None):
    from hashlib import sha256
    evidence = evidence or b''
    return 'p0:' + sha256(json.dumps([payload.hex(), evidence.hex(), hammer_confirmation], ensure_ascii=False).encode()).hexdigest()


P0_REGISTER_COLUMNS = P0_COLUMNS + ('source_id_normalized', 'price_kind_user_claim',
    'price_kind_original_evidence', 'original_observed_at', 'rights_reference',
    'original_price_evidence', 'data_status', 'purchase_recommendation')


def _p0_csv_register(payload, evidence):
    """Map the supplied blocked-reference register, preserving every original cell.

    A rights_reference alone is not a reviewed commercial-use permission.
    """
    source_rows = list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig')), delimiter=';'))
    originals = {}
    for row in source_rows:
        if None in row or set(row) != set(P0_COLUMNS) or any(v is None for v in row.values()):
            raise ValidationError('Original-CSV passt nicht zum P0-Register')
        key = row['auktions_id']
        if key in originals and originals[key] != row:
            raise ValidationError('Widersprüchliche P0-Originalzeilen')
        originals[key] = row
    reader = csv.DictReader(io.StringIO(evidence.decode('utf-8-sig')), delimiter=';')
    if reader.fieldnames != list(P0_REGISTER_COLUMNS):
        raise ValidationError('P0-Evidenz-CSV-Spalten unbekannt; explizite Abbildung erforderlich')
    entries, raw_entries = [], {}
    for index, row in enumerate(reader, 1):
        if index > MAX_LOTS or None in row or any(v is None for v in row.values()):
            raise ValidationError('P0-Evidenz-CSV-Zeile ungültig')
        key = row['source_id_normalized']
        if key != row['auktions_id'] or key not in originals or key in raw_entries:
            raise ValidationError('P0-Registerkennung fehlt oder ist doppelt/widersprüchlich')
        if {name:row[name] for name in P0_COLUMNS} != originals[key]:
            raise ValidationError('P0-Register und ursprüngliche CSV stimmen nicht überein')
        if row['purchase_recommendation'] != 'blocked' or row['data_status'] != 'P0_BLOCKED_PROVENANCE_RIGHTS':
            raise ValidationError('Dieses Registerformat belegt keine freigegebene P0-Nutzung')
        raw_entries[key] = dict(row)
        entries.append(dict(source='zoll-auktion', source_id=key, rights_status='unknown', rights_scope=None,
            rights_reference=row['rights_reference'] or None, reviewed_by=None, reviewed_at=None,
            source_observed_at=row['original_observed_at'] or None,
            time_reference=None, hammer_verification='unknown', hammer_reference=row['original_price_evidence'] or None))
        # The supplied format has no timestamp proof column. Keep filled timestamp as
        # an unverified raw declaration; never promote it to a source observation.
        entries[-1]['source_observed_at'] = None
    if not entries:
        raise ValidationError('P0-Evidenzregister ist leer')
    from hashlib import sha256
    return json.dumps(dict(schema_version=1,csv_sha256=sha256(payload).hexdigest(),entries=entries)).encode(), raw_entries


def parse_p0_csv(payload, evidence=None, *, hammer_confirmation=None, now=None):
    """Historical research only. A receipt timestamp never becomes source evidence.

    Evidence format is a proposed manual contract, not a claimed provider format.
    Rights declarations are not independently verified by parsing.
    """
    from datetime import datetime, timezone, date
    from hashlib import sha256
    from imports import _unique_object, _reject_constant
    from listings import timestamp, text
    now = now or datetime.now(timezone.utc)
    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES:
        raise ValidationError('P0-CSV maximal 2 MiB')
    if hammer_confirmation is not None:
        text(hammer_confirmation, 'hammer_confirmation')
    entries = {}
    raw_register = {}
    if evidence is not None:
        if not isinstance(evidence, bytes) or len(evidence) > MAX_BYTES:
            raise ValidationError('P0-Evidenz maximal 2 MiB')
        try:
            if not evidence.decode('utf-8-sig').lstrip().startswith('{'):
                evidence, raw_register = _p0_csv_register(payload, evidence)
            root = json.loads(evidence.decode('utf-8-sig'), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
            if (not isinstance(root, dict) or set(root) != {'schema_version', 'csv_sha256', 'entries'}
                    or type(root['schema_version']) is not int or root['schema_version'] != 1
                    or root['csv_sha256'] != sha256(payload).hexdigest()
                    or not isinstance(root['entries'], list) or len(root['entries']) > MAX_LOTS):
                raise ValidationError('P0-Evidenzvertrag oder CSV-Fingerprint ungültig')
            for entry in root['entries']:
                if not isinstance(entry, dict) or set(entry) != P0_EVIDENCE_FIELDS:
                    raise ValidationError('P0-Evidenzfelder ungültig')
                if entry['source'] != 'zoll-auktion' or not isinstance(entry['source_id'], str):
                    raise ValidationError('P0-Evidenzkennung ungültig')
                for name in ('rights_status', 'hammer_verification'):
                    choices = ('documented', 'unknown', 'restricted') if name == 'rights_status' else ('documented', 'unknown')
                    if not isinstance(entry[name], str) or entry[name] not in choices:
                        raise ValidationError('P0-Evidenzstatus ungültig')
                for name in P0_EVIDENCE_FIELDS - {'source', 'source_id', 'rights_status', 'hammer_verification'}:
                    if entry[name] is not None:
                        text(entry[name], name)
                for name in ('reviewed_at', 'source_observed_at'):
                    if entry[name] is not None and timestamp(entry[name], name) > now:
                        raise ValidationError('P0-Evidenzzeit liegt in der Zukunft')
                if entry['rights_status'] == 'documented' and (
                    entry['rights_scope'] != 'internal_commercial_import' or
                    not all(entry[n] for n in ('rights_reference','reviewed_by','reviewed_at'))):
                    raise ValidationError('Dokumentierte Nutzungsrechte brauchen Zweck, Beleg und Prüfer')
                if entry['source_observed_at'] and not entry['time_reference']:
                    raise ValidationError('Quellenzeit braucht einen Beleg')
                if entry['hammer_verification'] == 'documented' and not entry['hammer_reference']:
                    raise ValidationError('Zuschlagsverifikation braucht einen separaten Beleg')
                key = (entry['source'], entry['source_id'])
                if key in entries:
                    raise ValidationError('Doppelte P0-Evidenzkennung')
                entries[key] = entry
        except (UnicodeError, csv.Error, ValueError, TypeError, RecursionError) as error:
            if isinstance(error, ValidationError):
                raise
            raise ValidationError('P0-Evidenz unlesbar') from None
    try:
        reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')), delimiter=';')
        if reader.fieldnames != list(P0_COLUMNS):
            raise ValidationError('P0-CSV benötigt die dokumentierten deutschen Originalspalten')
        rows, provenance, seen_keys = [], [], set()
        for number, original in enumerate(reader, 1):
            if number > MAX_LOTS or None in original or any(v is None for v in original.values()):
                raise ValidationError('P0-CSV-Zeile ungültig oder Limit überschritten')
            if original['quelle'] != 'Zoll-Auktion':
                raise ValidationError('P0-CSV-Adapter unterstützt nur diese Recherchequelle')
            end_on = date.fromisoformat(original['auktionsende_datum'])
            amount = float(original['angezeigter_betrag_eur'].replace(',', '.'))
            if not isfinite(amount) or not 0 <= amount <= 1_000_000_000:
                raise ValidationError('P0-Betrag ungültig')
            from urllib.parse import urlsplit, parse_qs
            url = urlsplit(original['original_url'])
            if url.hostname not in {'www.zoll-auktion.de', 'zoll-auktion.de'} or (original['auktions_id'] not in url.path.split('/') and original['auktions_id'] not in parse_qs(url.query).get('id', [])):
                raise ValidationError('P0-URL und Quellenkennung passen nicht zusammen')
            key = ('zoll-auktion', original['auktions_id'])
            seen_keys.add(key)
            entry = entries.get(key)
            observed = timestamp(entry['source_observed_at'], 'source_observed_at') if entry and entry['source_observed_at'] else None
            issues = ['Historischer Recherchehinweis: kein aktuelles Kaufangebot']
            if not entry or entry['rights_status'] != 'documented':
                issues.append('Rechtsbeleg fehlt oder Nutzung eingeschränkt: manuell prüfen')
            if observed is None:
                issues.append('Quellenzeit unbelegt: Importzeit ist nur technischer Empfang')
            if not entry or entry['hammer_verification'] != 'documented':
                issues.append('Zuschlagspreis nicht unabhängig belegt')
            if hammer_confirmation is None:
                issues.append('Nutzerbestätigung des Zuschlagspreises fehlt')
            if original['datenhinweis']:
                issues.append('Originaler Datenhinweis bleibt prüfpflichtig erhalten')
            if original['status_am_2026_10_10'] != 'beendet':
                issues.append('Originalstatus und historische Zuschlagsbestätigung gesondert prüfen')
            receipt = now.isoformat()
            raw = dict(source=key[0], source_id=key[1], title=original['titel'], location=original['standort'],
                       listing_url=original['original_url'], observed_at=receipt,
                       ends_at=None, status='ended' if original['status_am_2026_10_10']=='beendet' else 'unknown',
                       bid_basis='unknown', currency='EUR', bid_kind='unknown', fee_model='unknown',
                       terms_reference='P0: Gebühren und Steuerbasis ungeklärt',
                       rights_reference=entry['rights_reference'] if entry and entry['rights_reference'] else 'P0: Rechtsbeleg ungeklärt',
                       fields={name:dict(value=None, origin='unknown', reference='P0: unbekannt; keine Finanzannahme') for name in FINANCIAL_FIELDS})
            rows.append(raw)
            provenance.append(dict(p0_research=True, source_key=list(key), observed_at=raw['observed_at'],
                observed_at_kind='import_receipt_only', imported_at=receipt,
                source_observed_at=observed.isoformat() if observed else None, original_status_as_of='2026-10-10', original_end_on=end_on.isoformat(), original_row=dict(original),
                price=dict(value=amount, currency='EUR', kind='hammer' if hammer_confirmation else 'unknown'),
                user_confirmation=dict(statement=hammer_confirmation, basis='user_statement', recorded_at=receipt),
                evidence=entry, original_evidence_row=raw_register.get(key[1]), review_issues=issues))
        if set(entries) - seen_keys:
            raise ValidationError('Evidenz verweist auf nicht vorhandene CSV-Angebote')
        batch = parse_import(json.dumps(dict(schema_version=1, listings=rows)).encode(), 'json', now)
        # Detect raw/provenance conflicts which are not visible in normalized unknown fields.
        originals = {}
        for row in provenance:
            key = tuple(row['source_key'])
            if key in originals and originals[key] != row['original_row']:
                raise ValidationError('Widersprüchliche P0-Originalzeilen')
            originals[key] = row['original_row']
        return ResearchBatch(batch.listings, batch.duplicates, tuple(provenance))
    except (UnicodeError, csv.Error, ValueError, TypeError, OverflowError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError('P0-CSV unlesbar oder Werte ungültig') from None
