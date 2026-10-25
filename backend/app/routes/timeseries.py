import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from ..matching import match_hours
from ..repository import get_actuals, get_forecasts, is_data_loaded
from ..schemas import TimeseriesPoint, TimeseriesResponse
from ..selection import ForecastRow, cutoff_for_delivery_day, select_vintage
from .metrics import _build_delivery_hours, _validate_dates

router = APIRouter()

CUTOFF_TIME = os.getenv("DECISION_CUTOFF_TIME", "09:20")


@router.get("/api/timeseries", response_model=TimeseriesResponse)
def timeseries(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
):
    if not is_data_loaded():
        raise HTTPException(
            status_code=503,
            detail={"error": "data_unavailable", "message": "Database not loaded."},
        )
    from_dt, to_dt = _validate_dates(from_date, to_date)

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

    matched, _, _, _ = match_hours(delivery_hours, selected_forecasts, actuals_by_time)

    points = [
        TimeseriesPoint(
            deliveryHour=h.deliveryHour.strftime("%Y-%m-%dT%H:%M:%SZ"),
            forecast=h.forecast_mw,
            actual=h.actual_mw,
            error=h.error_mw,
            selectedPublishTime=(
                h.selectedPublishTime.strftime("%Y-%m-%dT%H:%M:%SZ")
                if h.selectedPublishTime
                else None
            ),
            complete=h.complete,
        )
        for h in matched
    ]
    return TimeseriesResponse(units="MW", points=points)
