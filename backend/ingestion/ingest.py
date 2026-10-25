"""Fetch FUELHH actuals + WINDFOR forecasts for Jan 2026 and store in SQLite."""

import asyncio
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from pydantic import ValidationError

from .db import get_connection, init_schema, insert_actuals, insert_forecasts, upsert_meta
from .elexon_client import fetch_fuelhh, fetch_windfor
from .models import FuelhhRecord, WindforRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
DB_PATH = os.getenv("WIND_DB_PATH", str(Path(__file__).parent.parent / "data" / "wind_data.db"))
CUTOFF_TIME = os.getenv("DECISION_CUTOFF_TIME", "09:20")
PAGE_SIZE = 5000

DELIVERY_FROM = date(2026, 1, 1)
DELIVERY_TO = date(2026, 1, 31)
FORECAST_PUBLISH_FROM = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
FORECAST_PUBLISH_TO = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)


def parse_cutoff(cutoff_str: str, day: date) -> datetime:
    h, m = map(int, cutoff_str.split(":"))
    return datetime(day.year, day.month, day.day, h, m, 0, tzinfo=timezone.utc)


async def ingest_windfor(client: httpx.AsyncClient, conn) -> dict:
    notes: dict = {"windfor_per_day": {}, "windfor_dropped": 0, "windfor_retained": 0}
    current = FORECAST_PUBLISH_FROM.date()
    end = FORECAST_PUBLISH_TO.date()

    while current <= end:
        day_from = datetime(current.year, current.month, current.day, 0, 0, 0, tzinfo=timezone.utc)
        day_to = datetime(current.year, current.month, current.day, 23, 59, 59, tzinfo=timezone.utc)

        records = await _fetch_windfor_day(client, day_from, day_to)

        validated, dropped = _validate_windfor(records)
        notes["windfor_dropped"] += dropped
        notes["windfor_retained"] += len(validated)

        publish_times = sorted(set(r["publishTime"] for r in validated))
        notes["windfor_per_day"][str(current)] = publish_times

        if len(publish_times) == 0:
            logger.error("ZERO distinct publishTimes for day %s", current)
            raise RuntimeError(f"No WINDFOR records for {current}")
        elif len(publish_times) == 1:
            logger.warning("Single vintage day: %s publishTime=%s", current, publish_times[0])

        delivery_day = current + timedelta(days=1)
        if DELIVERY_FROM <= delivery_day <= DELIVERY_TO:
            cutoff_dt = parse_cutoff(CUTOFF_TIME, current)
            eligible = [pt for pt in publish_times if pt <= cutoff_dt.isoformat().replace("+00:00", "Z")]
            if not eligible:
                logger.warning(
                    "No eligible vintage for delivery day %s (cutoff %s)", delivery_day, cutoff_dt
                )

        insert_forecasts(conn, validated)
        logger.info("WINDFOR %s: %d records, %d publishTimes", current, len(validated), len(publish_times))
        current += timedelta(days=1)

    return notes


async def _fetch_windfor_day(
    client: httpx.AsyncClient, day_from: datetime, day_to: datetime
) -> list[dict]:
    records = await fetch_windfor(client, BASE_URL, day_from, day_to, PAGE_SIZE)
    if len(records) >= PAGE_SIZE:
        logger.error(
            "Possible truncation: %d records == pageSize %d for %s",
            len(records),
            PAGE_SIZE,
            day_from.date(),
        )
        mid = day_from + (day_to - day_from) / 2
        part1 = await fetch_windfor(client, BASE_URL, day_from, mid, PAGE_SIZE)
        part2 = await fetch_windfor(client, BASE_URL, mid, day_to, PAGE_SIZE)
        records = part1 + part2
    return records


def _validate_windfor(raw: list[dict]) -> tuple[list[dict], int]:
    valid, dropped = [], 0
    for row in raw:
        try:
            rec = WindforRecord.model_validate(row)
            valid.append({
                "startTime": rec.startTime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishTime": rec.publishTime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "generation_mw": rec.generation_mw,
            })
        except ValidationError as e:
            logger.warning("Dropped WINDFOR row: %s | error: %s", row, e)
            dropped += 1
    return valid, dropped


async def ingest_fuelhh(client: httpx.AsyncClient, conn) -> dict:
    notes: dict = {"fuelhh_dropped": 0, "fuelhh_retained": 0}
    current = DELIVERY_FROM
    while current <= DELIVERY_TO:
        week_end = min(current + timedelta(days=6), DELIVERY_TO)
        records = await fetch_fuelhh(client, BASE_URL, str(current), str(week_end))
        validated, dropped = _validate_fuelhh(records)
        notes["fuelhh_dropped"] += dropped
        notes["fuelhh_retained"] += len(validated)
        insert_actuals(conn, validated)
        logger.info("FUELHH %s to %s: %d records", current, week_end, len(validated))
        current = week_end + timedelta(days=1)
    return notes


def _validate_fuelhh(raw: list[dict]) -> tuple[list[dict], int]:
    valid, dropped = [], 0
    for row in raw:
        try:
            rec = FuelhhRecord.model_validate(row)
            valid.append({
                "startTime": rec.startTime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "settlementDate": rec.settlementDate,
                "settlementPeriod": rec.settlementPeriod,
                "generation_mw": rec.generation_mw,
            })
        except ValidationError as e:
            logger.warning("Dropped FUELHH row: %s | error: %s", row, e)
            dropped += 1
    return valid, dropped


async def main() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(DB_PATH)
    init_schema(conn)

    logger.info("Starting ingestion. DB: %s", DB_PATH)
    async with httpx.AsyncClient() as client:
        windfor_notes = await ingest_windfor(client, conn)
        fuelhh_notes = await ingest_fuelhh(client, conn)

    ingestion_notes = {**windfor_notes, **fuelhh_notes}
    upsert_meta(conn, {
        "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff_definition": f"D-1 {CUTOFF_TIME} UTC (provisional — configurable via DECISION_CUTOFF_TIME)",
        "source_urls": [
            f"{BASE_URL}/datasets/WINDFOR",
            f"{BASE_URL}/datasets/FUELHH",
        ],
        "timezone_note": "UTC == UK local for Jan 2026 (no DST)",
        "delivery_date_from": str(DELIVERY_FROM),
        "delivery_date_to": str(DELIVERY_TO),
        "forecast_publish_from": FORECAST_PUBLISH_FROM.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "forecast_publish_to": FORECAST_PUBLISH_TO.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ingestion_notes": ingestion_notes,
    })
    conn.close()
    logger.info("Ingestion complete. Notes: %s", json.dumps(ingestion_notes, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
