from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ActualHalfHour:
    startTime: datetime
    generation_mw: float | None


@dataclass
class MatchedHour:
    deliveryHour: datetime
    forecast_mw: float | None
    actual_mw: float | None
    error_mw: float | None
    selectedPublishTime: datetime | None
    complete: bool
    missingForecast: bool
    missingActual: bool


def aggregate_actuals(
    half_hours: list[ActualHalfHour], delivery_hour: datetime
) -> tuple[float | None, bool]:
    """Average two half-hour actuals for the delivery hour. Returns (value, missingActual)."""
    h_start = delivery_hour
    h_mid = delivery_hour + timedelta(minutes=30)

    vals = {hh.startTime: hh.generation_mw for hh in half_hours}
    a = vals.get(h_start)
    b = vals.get(h_mid)

    if a is None or b is None:
        return None, True
    return (a + b) / 2.0, False


def match_hours(
    delivery_hours: list[datetime],
    selected_forecasts: dict[datetime, tuple[float | None, datetime | None]],
    actuals_by_time: dict[datetime, float | None],
) -> tuple[list[MatchedHour], int, int, int]:
    """
    Match forecasts to actuals for each delivery hour.
    selected_forecasts: {delivery_hour -> (generation_mw, publishTime)}
    actuals_by_time: {half_hour_startTime -> generation_mw}
    Returns: (matched_hours, hoursTotal, hoursComplete, hoursIncomplete)
    """
    matched = []
    hours_complete = 0
    hours_incomplete = 0

    for dh in sorted(delivery_hours):
        forecast_entry = selected_forecasts.get(dh)
        missing_forecast = forecast_entry is None
        forecast_mw: float | None = None
        publish_time: datetime | None = None
        if forecast_entry is not None:
            forecast_mw, publish_time = forecast_entry

        half_hours = [
            ActualHalfHour(startTime=dh, generation_mw=actuals_by_time.get(dh)),
            ActualHalfHour(
                startTime=dh + timedelta(minutes=30),
                generation_mw=actuals_by_time.get(dh + timedelta(minutes=30)),
            ),
        ]
        actual_mw, missing_actual = aggregate_actuals(half_hours, dh)

        complete = not missing_forecast and not missing_actual
        error_mw = (
            (forecast_mw - actual_mw)
            if complete and forecast_mw is not None and actual_mw is not None
            else None
        )

        if complete:
            hours_complete += 1
        else:
            hours_incomplete += 1

        matched.append(MatchedHour(
            deliveryHour=dh,
            forecast_mw=forecast_mw if not missing_forecast else None,
            actual_mw=actual_mw,
            error_mw=error_mw,
            selectedPublishTime=publish_time,
            complete=complete,
            missingForecast=missing_forecast,
            missingActual=missing_actual,
        ))

    hours_total = hours_complete + hours_incomplete
    return matched, hours_total, hours_complete, hours_incomplete
