from fastapi import APIRouter, HTTPException

from ..repository import get_meta, is_data_loaded
from ..schemas import MetaResponse

router = APIRouter()

GENERATION_UNITS_NOTE = (
    "FUELHH generation treated as average MW power over the 30-min settlement period. "
    "Physical-evidence basis: observed values 10,000-16,000 imply MW scale; "
    "MWh interpretation would imply 20,000-32,000 MW instantaneous power, "
    "exceeding UK installed wind capacity (~25 GW). "
    "Official Elexon documentation was inaccessible during design."
)


@router.get("/api/meta", response_model=MetaResponse)
def meta():
    if not is_data_loaded():
        raise HTTPException(
            status_code=503,
            detail={"error": "data_unavailable", "message": "Database not loaded."},
        )
    row = get_meta()
    if not row:
        raise HTTPException(
            status_code=503,
            detail={"error": "data_unavailable", "message": "Database not loaded."},
        )
    return MetaResponse(
        ingestedAt=row.ingested_at,
        cutoff=row.cutoff_definition or "D-1 09:20 UTC (provisional)",
        units=row.units,
        timezoneNote=row.timezone_note or "UTC == UK local for Jan 2026 (no DST)",
        sources=row.source_urls or ["FUELHH", "WINDFOR"],
        deliveryDateRange={
            "from": row.delivery_date_from or "2026-01-01",
            "to": row.delivery_date_to or "2026-01-31",
        },
        forecastPublishRange={
            "from": row.forecast_publish_from or "2025-12-31T00:00:00Z",
            "to": row.forecast_publish_to or "2026-01-31T23:59:59Z",
        },
        generationUnitsNote=GENERATION_UNITS_NOTE,
    )
