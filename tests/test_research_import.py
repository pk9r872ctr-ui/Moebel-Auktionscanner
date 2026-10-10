"""Proposed schema fixtures are synthetic; no genuine auction records."""
import csv
import io
import pytest
from listings import ValidationError
from research_import import parse_research_csv
from test_imports import NOW


def row():
    return dict(source='synthetic', source_id='1', title='TEST ONLY Stuhl', listing_url='https://example.org/lot/1', observed_at='2026-10-10T11:00:00Z', rights_reference='Synthetic owned fixture', currency='EUR', price='123,45', price_kind='current', description='fiktiv', extra='preserve me')


def encode(*rows):
    out = io.StringIO(); writer = csv.DictWriter(out, list(rows[0]), delimiter=';')
    writer.writeheader(); writer.writerows(rows)
    return out.getvalue().encode()


@pytest.mark.parametrize('kind', ['current', 'starting', 'minimum', 'manual', 'unknown', 'hammer', 'total'])
def test_price_semantics(kind):
    data = row(); data['price_kind'] = kind
    result = parse_research_csv(encode(data), now=NOW)
    lot = result.listings[0]
    assert result.provenance[0]['original_row']['extra'] == 'preserve me'
    assert result.provenance[0]['price']['kind'] == kind
    assert (lot.fields['current_bid'].value is None) == (kind in {'unknown', 'hammer', 'total'})
    assert lot.fields['transport'].origin == 'unknown'


def test_duplicates_and_conflict():
    data = row()
    assert parse_research_csv(encode(data, data), now=NOW).duplicates == 1
    other = dict(data, price='99')
    with pytest.raises(ValidationError): parse_research_csv(encode(data, other), now=NOW)


@pytest.mark.parametrize('field,value', [('currency',''), ('currency','USD'), ('observed_at',''), ('rights_reference',''), ('price','NaN'), ('price_kind','selling')])
def test_reject_missing_and_invalid(field, value):
    data = row(); data[field] = value
    with pytest.raises(ValidationError): parse_research_csv(encode(data), now=NOW)


def test_mapping_and_duplicate_headers():
    data = row(); data['Kennung'] = data.pop('source_id')
    assert parse_research_csv(encode(data), mapping={'source_id': 'Kennung'}, now=NOW).listings[0].source_id == '1'
    with pytest.raises(ValidationError): parse_research_csv(b'source;source\na;b\n', now=NOW)


def test_mapping_cannot_alias_two_fields():
    with pytest.raises(ValidationError):
        parse_research_csv(encode(row()), mapping={'source': 'source_id'}, now=NOW)
