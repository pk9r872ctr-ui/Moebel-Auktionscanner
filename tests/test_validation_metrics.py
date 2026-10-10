import pytest
from listings import Listing
from test_imports import raw_listing, NOW
from validation_metrics import practice_metrics


def test_no_fabricated_economic_success():
    lots = [Listing.parse(dict(raw_listing(), source_id=str(i)), NOW) for i in range(20)]
    result = practice_metrics(lots)
    assert result['dataset_kind'] == 'synthetic'
    assert not result['practice_20_real_met']
    assert result['time_savings_seconds'] is None
    assert result['realized_profitable_purchases'] is None


def test_measured_baseline_and_rates():
    result = practice_metrics([Listing.parse(raw_listing(), NOW)], input_count=4, duplicates=2, errors=1, elapsed_seconds=1, manual_seconds=5, baseline_seconds=20)
    assert result['time_savings_seconds'] == 14
    assert result['duplicate_fraction'] == .5
    assert result['error_fraction'] == .25


@pytest.mark.parametrize('kwargs', [{'duplicates': -1}, {'elapsed_seconds': float('nan')}, {'input_count': 0}, {'manual_seconds': True}])
def test_metrics_validation(kwargs):
    with pytest.raises(ValueError): practice_metrics([Listing.parse(raw_listing(), NOW)], **kwargs)


def test_assessment_blockers():
    result = practice_metrics([Listing.parse(raw_listing(), NOW)], assessments=[{'status': 'blocked', 'blockers': ['tax unclear']}])
    assert result['not_reliably_assessable'] == 1
    assert result['blocker_counts'] == {'tax unclear': 1}
    with pytest.raises(ValueError): practice_metrics([], assessments=[{'status': 'blocked'}])
