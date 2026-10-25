from datetime import datetime, timezone

from backend.app.matching import ActualHalfHour, aggregate_actuals, match_hours

UTC = timezone.utc


def dt(hour: int, minute: int = 0, day: int = 1) -> datetime:
    return datetime(2026, 1, day, hour, minute, 0, tzinfo=UTC)


def test_both_half_hours_present():
    dh = dt(0)
    actual_val, missing = aggregate_actuals(
        [
            ActualHalfHour(startTime=dt(0), generation_mw=15000.0),
            ActualHalfHour(startTime=dt(0, 30), generation_mw=15200.0),
        ],
        dh,
    )
    assert not missing
    assert abs(actual_val - 15100.0) < 1e-9


def test_one_half_hour_null():
    dh = dt(0)
    actual_val, missing = aggregate_actuals(
        [
            ActualHalfHour(startTime=dt(0), generation_mw=None),
            ActualHalfHour(startTime=dt(0, 30), generation_mw=15200.0),
        ],
        dh,
    )
    assert missing
    assert actual_val is None


def test_no_forecast_missing_forecast():
    hours = [dt(0)]
    selected = {}
    actuals = {dt(0): 15000.0, dt(0, 30): 15200.0}
    matched, total, complete, incomplete = match_hours(hours, selected, actuals)
    assert total == 1
    assert complete == 0
    assert incomplete == 1
    assert matched[0].missingForecast
    assert not matched[0].missingActual


def test_both_missing():
    hours = [dt(0)]
    selected = {}
    actuals = {}
    matched, total, complete, incomplete = match_hours(hours, selected, actuals)
    assert incomplete == 1
    assert complete == 0
    assert total == 1


def test_hours_complete_plus_incomplete_equals_total():
    hours = [dt(0), dt(1), dt(2)]
    selected = {dt(0): (14000.0, datetime(2025, 12, 31, 7, 30, tzinfo=UTC))}
    actuals = {dt(0): 15000.0, dt(0, 30): 15200.0}
    matched, total, complete, incomplete = match_hours(hours, selected, actuals)
    assert complete + incomplete == total


def test_boundary_hour_00():
    hours = [dt(0)]
    pub = datetime(2025, 12, 31, 7, 30, 0, tzinfo=UTC)
    selected = {dt(0): (14000.0, pub)}
    actuals = {dt(0): 15000.0, dt(0, 30): 15200.0}
    matched, total, complete, incomplete = match_hours(hours, selected, actuals)
    assert complete == 1


def test_boundary_hour_23():
    hours = [dt(23)]
    pub = datetime(2025, 12, 31, 7, 30, 0, tzinfo=UTC)
    selected = {dt(23): (14000.0, pub)}
    actuals = {dt(23): 15000.0, dt(23, 30): 15200.0}
    matched, total, complete, incomplete = match_hours(hours, selected, actuals)
    assert complete == 1


def test_genuine_zero_actual_is_complete():
    hours = [dt(0)]
    pub = datetime(2025, 12, 31, 7, 30, 0, tzinfo=UTC)
    selected = {dt(0): (500.0, pub)}
    actuals = {dt(0): 0.0, dt(0, 30): 0.0}
    matched, total, complete, incomplete = match_hours(hours, selected, actuals)
    assert complete == 1
    assert matched[0].actual_mw == 0.0
