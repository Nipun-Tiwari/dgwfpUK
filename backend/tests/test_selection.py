from datetime import datetime, timedelta, timezone

from backend.app.selection import ForecastRow, cutoff_for_delivery_day, select_vintage

UTC = timezone.utc
JAN1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
DEC31_CUTOFF = datetime(2025, 12, 31, 9, 20, 0, tzinfo=UTC)


def test_vintage_at_exactly_cutoff_eligible():
    forecasts = [ForecastRow(startTime=JAN1, publishTime=DEC31_CUTOFF, generation_mw=14000.0)]
    result = select_vintage(forecasts, JAN1, DEC31_CUTOFF)
    assert not result.missingForecast
    assert result.publishTime == DEC31_CUTOFF


def test_vintage_one_second_after_cutoff_excluded():
    post_cutoff = DEC31_CUTOFF + timedelta(seconds=1)
    forecasts = [ForecastRow(startTime=JAN1, publishTime=post_cutoff, generation_mw=14000.0)]
    result = select_vintage(forecasts, JAN1, DEC31_CUTOFF)
    assert result.missingForecast


def test_multiple_vintages_max_selected():
    t1 = datetime(2025, 12, 31, 4, 30, 0, tzinfo=UTC)
    t2 = datetime(2025, 12, 31, 7, 30, 0, tzinfo=UTC)
    forecasts = [
        ForecastRow(startTime=JAN1, publishTime=t1, generation_mw=13000.0),
        ForecastRow(startTime=JAN1, publishTime=t2, generation_mw=14000.0),
    ]
    result = select_vintage(forecasts, JAN1, DEC31_CUTOFF)
    assert result.publishTime == t2
    assert result.generation_mw == 14000.0


def test_no_eligible_vintage():
    t_post = datetime(2025, 12, 31, 10, 0, 0, tzinfo=UTC)
    forecasts = [ForecastRow(startTime=JAN1, publishTime=t_post, generation_mw=14000.0)]
    result = select_vintage(forecasts, JAN1, DEC31_CUTOFF)
    assert result.missingForecast
    assert result.generation_mw is None


def test_jan1_delivery_dec31_vintage_eligible():
    pub = datetime(2025, 12, 31, 7, 30, 0, tzinfo=UTC)
    forecasts = [ForecastRow(startTime=JAN1, publishTime=pub, generation_mw=14000.0)]
    result = select_vintage(forecasts, JAN1, DEC31_CUTOFF)
    assert not result.missingForecast


def test_jan31_delivery():
    jan31 = datetime(2026, 1, 31, 0, 0, 0, tzinfo=UTC)
    jan30_cutoff = datetime(2026, 1, 30, 9, 20, 0, tzinfo=UTC)
    pub_eligible = datetime(2026, 1, 30, 7, 30, 0, tzinfo=UTC)
    pub_late = datetime(2026, 1, 30, 9, 30, 0, tzinfo=UTC)
    forecasts = [
        ForecastRow(startTime=jan31, publishTime=pub_eligible, generation_mw=12000.0),
        ForecastRow(startTime=jan31, publishTime=pub_late, generation_mw=12500.0),
    ]
    result = select_vintage(forecasts, jan31, jan30_cutoff)
    assert result.publishTime == pub_eligible
    assert not result.missingForecast


def test_cutoff_for_delivery_day():
    jan1 = datetime(2026, 1, 1, tzinfo=UTC)
    cutoff = cutoff_for_delivery_day(jan1, "09:20")
    assert cutoff == datetime(2025, 12, 31, 9, 20, 0, tzinfo=UTC)
