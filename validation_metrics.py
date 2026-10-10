"""Reproducible practice metrics, without invented time savings or realized profit."""
from math import isfinite


def practice_metrics(listings, *, real_data=False, input_count=None, duplicates=0,
                     errors=0, elapsed_seconds=0, manual_seconds=None, baseline_seconds=None, assessments=None):
    lots = list(listings)
    if len({lot.key for lot in lots}) != len(lots):
        raise ValueError('Metrics require unique processed listings; count duplicates separately')
    counts = [duplicates, errors, len(lots) if input_count is None else input_count]
    if any(type(n) is not int or n < 0 for n in counts):
        raise ValueError('Counts must be nonnegative integers')
    total = counts[2]
    if total < len(lots) + duplicates + errors:
        raise ValueError('Input count smaller than processed outcomes')
    for value in (elapsed_seconds, manual_seconds, baseline_seconds):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value) or value < 0):
            raise ValueError('Times must be finite nonnegative seconds')
    complete = sum(all(d.value is not None for d in lot.fields.values()) for lot in lots)
    assessed = list(assessments) if assessments is not None else None
    if assessed is not None and len(assessed) != len(lots):
        raise ValueError('One assessment per processed listing required')
    blocked = sum(a.get('status') == 'blocked' for a in assessed) if assessed is not None else None
    reasons = {}
    for assessment in assessed or []:
        for reason in assessment.get('blockers', []):
            reasons[reason] = reasons.get(reason, 0) + 1
    return {'dataset_kind': 'real' if real_data else 'synthetic', 'input_count': total,
            'processed_unique': len(lots), 'complete_financial_records': complete,
            'complete_fraction': complete / len(lots) if lots else None,
            'duplicates': duplicates, 'duplicate_fraction': duplicates / total if total else None,
            'errors': errors, 'error_fraction': errors / total if total else None,
            'elapsed_seconds': elapsed_seconds, 'manual_seconds': manual_seconds,
            'manual_baseline_seconds': baseline_seconds,
            'time_savings_seconds': baseline_seconds - elapsed_seconds - manual_seconds if baseline_seconds is not None and manual_seconds is not None else None,
            'not_reliably_assessable': blocked,
            'not_reliably_assessable_fraction': blocked / len(lots) if blocked is not None and lots else None,
            'blocker_counts': reasons if assessed is not None else None,
            'interesting_candidates': None, 'manually_verified_candidates': None,
            'realized_profitable_purchases': None,
            'economic_validation_status': 'not established',
            'practice_20_real_met': bool(real_data and len(lots) >= 20),
            'note': 'Financial completeness does not establish tax correctness, freshness or profitability.'}
