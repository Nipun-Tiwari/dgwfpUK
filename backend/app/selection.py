from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class ForecastRow:
    startTime: datetime
    publishTime: datetime
    generation_mw: float | None


@dataclass
class SelectedForecast:
    startTime: datetime
    publishTime: datetime | None
    generation_mw: float | None
    missingForecast: bool


def select_vintage(
    forecasts: list[ForecastRow],
    delivery_hour: datetime,
    cutoff_dt: datetime,
) -> SelectedForecast:
    """Select forecast with max publishTime <= cutoff_dt for delivery_hour."""
    assert delivery_hour.tzinfo is not None, "delivery_hour must be timezone-aware"
    assert cutoff_dt.tzinfo is not None, "cutoff_dt must be timezone-aware"

    eligible = [
        f for f in forecasts
        if f.startTime == delivery_hour and f.publishTime <= cutoff_dt
    ]
    if not eligible:
        return SelectedForecast(
            startTime=delivery_hour,
            publishTime=None,
            generation_mw=None,
            missingForecast=True,
        )
    best = max(eligible, key=lambda f: f.publishTime)
    return SelectedForecast(
        startTime=delivery_hour,
        publishTime=best.publishTime,
        generation_mw=best.generation_mw,
        missingForecast=False,
    )


def cutoff_for_delivery_day(delivery_date: datetime, cutoff_time_str: str) -> datetime:
    """Compute cutoff datetime for a delivery day. cutoff is on D-1 at HH:MM UTC."""
    h, m = map(int, cutoff_time_str.split(":"))
    prev_day = delivery_date.date() - timedelta(days=1)
    return datetime(prev_day.year, prev_day.month, prev_day.day, h, m, 0, tzinfo=timezone.utc)
