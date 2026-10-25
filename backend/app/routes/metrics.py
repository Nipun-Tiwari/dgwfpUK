import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..analytics import compute_metrics
from ..matching import match_hours
from ..repository import get_actuals, get_forecasts, is_data_loaded
from ..schemas import MetricsResponse
from ..selection import ForecastRow, cutoff_for_delivery_day, select_vintage

router = APIRouter()

MIN_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
MAX_DATE = datetime(2026, 1, 31, tzinfo=timezone.utc)
CUTOFF_TIME = os.getenv("DECISION_CUTOFF_TIME", "09:20")


def _validate_dates(from_date: str, to_date: str) -> tuple[datetime, datetime]:
    try:
        from_dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        to_dt = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_date", "message": "Invalid date format."},
        )
    if from_dt > to_dt:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_date_range", "message": "from must be <= to"},
        )
    if from_dt < MIN_DATE or to_dt > MAX_DATE:
        raise HTTPException(
            status_code=400,
            detail={"error": "out_of_range", "message": "dates must be within 2026-01-01 to 2026-01-31"},
        )
    return from_dt, to_dt


def _build_delivery_hours(from_dt: datetime, to_dt: datetime) -> list[datetime]:
    hours = []
    current = from_dt
    end = to_dt + timedelta(days=1)
    while current < end:
        hours.append(current)
        current += timedelta(hours=1)
    return hours


def _process_window(from_dt: datetime, to_dt: datetime):
    delivery_hours = _build_delivery_hours(from_dt, to_dt)
    fetch_end = to_dt + timedelta(days=1)
    forecast_rows = get_forecasts(from_dt, fetch_end)
    actual_rows = get_actuals(from_dt, fetch_end)

    forecast_objs = [
        ForecastRow(startTime=r.startTime, publishTime=r.publishTime, generation_mw=r.generation_mw)
        for r in forecast_rows
    ]
    actuals_by_time = {r.startTime: r.generation_mw for r in actual_rows}

    selected_forecasts: dict[datetime, tuple] = {}
    for dh in delivery_hours:
        cutoff_dt = cutoff_for_delivery_day(dh, CUTOFF_TIME)
        sel = select_vintage(forecast_objs, dh, cutoff_dt)
        if not sel.missingForecast:
            selected_forecasts[dh] = (sel.generation_mw, sel.publishTime)

    matched, _total, _complete, _incomplete = match_hours(
        delivery_hours, selected_forecasts, actuals_by_time
    )
    return matched


@router.get("/api/metrics", response_model=MetricsResponse)
def metrics(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
):
    if not is_data_loaded():
        raise HTTPException(
            status_code=503,
            detail={"error": "data_unavailable", "message": "Database not loaded."},
        )
    from_dt, to_dt = _validate_dates(from_date, to_date)
    matched = _process_window(from_dt, to_dt)
    result = compute_metrics(matched)
    return MetricsResponse(
        mae=result.mae,
        rmse=result.rmse,
        bias=result.bias,
        nmae=result.nmae,
        nrmse=result.nrmse,
        normalizedOmitted=result.normalizedOmitted,
        completeness=result.completeness,
        hoursTotal=result.hoursTotal,
        hoursComplete=result.hoursComplete,
        hoursIncomplete=result.hoursIncomplete,
        hoursMissingForecast=result.hoursMissingForecast,
        hoursMissingActual=result.hoursMissingActual,
    )
