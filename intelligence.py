"""Explainable text derivations; never modify source listings or infer profitability."""
import re
from datetime import datetime, timezone
from listings import timestamp

CATEGORY_TERMS = {
    'seating': ('bürostuhl', 'stuhl', 'stühle', 'sessel', 'sofa', 'couch'),
    'tables': ('schreibtisch', 'tisch', 'tische'),
    'storage': ('schrank', 'schränke', 'regal', 'kommode', 'sideboard'),
    'beds': ('bett', 'betten'),
}
BRANDS = ('vitra', 'usm', 'herman miller', 'steelcase', 'interstuhl', 'wilkhahn', 'thonet', 'ikea')
MATERIALS = ('massivholz', 'eiche', 'buche', 'holz', 'metall', 'leder', 'glas', 'kunststoff')


def _matches(text, terms):
    return [m for term in terms for m in re.finditer(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I)]


def _derived(matches, value=None):
    if not matches:
        return {'value': None, 'origin': 'unknown', 'evidence': []}
    return {'value': value if value is not None else list(dict.fromkeys(m.group().lower() for m in matches)),
            'origin': 'derived', 'method': 'literal token match v1; manual review required',
            'evidence': [{'text': m.group(), 'start': m.start(), 'end': m.end()} for m in matches]}


def analyze_listing(lot, description=''):
    """Evidence offsets refer to title + newline + supplied original description."""
    source_text = lot.title + '\n' + description
    categories = {category: _matches(source_text, terms) for category, terms in CATEGORY_TERMS.items()}
    found = [category for category, matches in categories.items() if matches]
    quantity = list(re.finditer(r'\b([1-9][0-9]*)\s*(?:stück|stk\.?)(?!\w)', source_text, re.I))
    amounts = {int(m.group(1)) for m in quantity}
    return {
        'analysis_version': 1, 'source_key': list(lot.key),
        'category': _derived([m for matches in categories.values() for m in matches], found),
        'brand': _derived(_matches(source_text, BRANDS)),
        'material': _derived(_matches(source_text, MATERIALS)),
        'damage': _derived(_matches(source_text, ('beschädigt', 'defekt', 'kratzer', 'risse'))),
        'condition': _derived(_matches(source_text, ('gebraucht', 'neuwertig', 'ungeprüft'))),
        'quantity': _derived(quantity, next(iter(amounts))) if len(amounts) == 1 else {'value': None, 'origin': 'unknown', 'evidence': [], 'reason': 'missing or ambiguous explicit Stück/Stk count'},
        'model': {'value': None, 'origin': 'unknown', 'evidence': []},
        'location': {'value': lot.location, 'origin': 'observed', 'reference': lot.listing_url},
        'warnings': ['Text matches may include negation or conflicting descriptions; no purchase recommendation.'],
    }


def possible_duplicates(listings):
    """Conservative cross-source candidates only; no deletion or merging."""
    lots = list(listings)
    candidates = []
    for i, left in enumerate(lots):
        for right in lots[i + 1:]:
            if left.source == right.source:
                continue
            normalized = lambda text: ' '.join(re.findall(r'\w+', text.casefold()))
            if normalized(left.title) == normalized(right.title) and normalized(left.location) == normalized(right.location):
                candidates.append({'left': list(left.key), 'right': list(right.key), 'status': 'possible',
                                   'reason': 'same normalized title and location; manual review required'})
    return candidates


def filter_listings(listings, criteria, now=None):
    """Pure filters; unknown prices excluded from bounded price searches."""
    now = now or datetime.now(timezone.utc)
    result = []
    for lot in listings:
        if criteria.get('source') and lot.source != criteria['source']: continue
        if criteria.get('status') and lot.status != criteria['status']: continue
        if criteria.get('location') and criteria['location'].casefold() not in lot.location.casefold(): continue
        if criteria.get('search') and criteria['search'].casefold() not in lot.title.casefold(): continue
        if criteria.get('category') and criteria['category'] not in (analyze_listing(lot)['category']['value'] or []): continue
        price = lot.fields['current_bid'].value
        if 'min_price' in criteria and (price is None or price < criteria['min_price']): continue
        if 'max_price' in criteria and (price is None or price > criteria['max_price']): continue
        if criteria.get('ends_before') and (not lot.ends_at or timestamp(lot.ends_at, 'ends_at') > timestamp(criteria['ends_before'], 'ends_before')): continue
        if criteria.get('upcoming') and (not lot.ends_at or timestamp(lot.ends_at, 'ends_at') <= now): continue
        complete = all(d.value is not None for d in lot.fields.values())
        if criteria.get('quality') == 'complete' and not complete: continue
        if criteria.get('quality') == 'incomplete' and complete: continue
        result.append(lot)
    return result
