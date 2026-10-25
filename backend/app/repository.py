import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = os.getenv("WIND_DB_PATH", str(Path(__file__).parent.parent / "data" / "wind_data.db"))


@dataclass
class ForecastRecord:
    startTime: datetime
    publishTime: datetime
    generation_mw: Optional[float]


@dataclass
class ActualRecord:
    startTime: datetime
    settlementPeriod: int
    generation_mw: Optional[float]


@dataclass
class MetaRecord:
    ingested_at: str
    cutoff_definition: Optional[str]
    source_urls: list[str]
    units: str
    timezone_note: Optional[str]
    delivery_date_from: Optional[str]
    delivery_date_to: Optional[str]
    forecast_publish_from: Optional[str]
    forecast_publish_to: Optional[str]


def _utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_data_loaded() -> bool:
    if not Path(DB_PATH).exists():
        return False
    try:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM meta").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def get_meta() -> Optional[MetaRecord]:
    if not Path(DB_PATH).exists():
        return None
    conn = get_db()
    row = conn.execute("SELECT * FROM meta LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    return MetaRecord(
        ingested_at=row["ingested_at"],
        cutoff_definition=row["cutoff_definition"],
        source_urls=json.loads(row["source_urls"] or "[]"),
        units=row["units"] or "MW",
        timezone_note=row["timezone_note"],
        delivery_date_from=row["delivery_date_from"],
        delivery_date_to=row["delivery_date_to"],
        forecast_publish_from=row["forecast_publish_from"],
        forecast_publish_to=row["forecast_publish_to"],
    )


def get_forecasts(from_dt: datetime, to_dt: datetime) -> list[ForecastRecord]:
    conn = get_db()
    rows = conn.execute(
        """SELECT startTime, publishTime, generation_mw FROM forecasts
           WHERE startTime >= ? AND startTime < ?
           ORDER BY startTime, publishTime""",
        (from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), to_dt.strftime("%Y-%m-%dT%H:%M:%SZ")),
    ).fetchall()
    conn.close()
    return [
        ForecastRecord(
            startTime=_utc(r["startTime"]),
            publishTime=_utc(r["publishTime"]),
            generation_mw=r["generation_mw"],
        )
        for r in rows
    ]


def get_actuals(from_dt: datetime, to_dt: datetime) -> list[ActualRecord]:
    conn = get_db()
    rows = conn.execute(
        """SELECT startTime, settlementPeriod, generation_mw FROM actuals
           WHERE startTime >= ? AND startTime < ?
           ORDER BY startTime""",
        (from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), to_dt.strftime("%Y-%m-%dT%H:%M:%SZ")),
    ).fetchall()
    conn.close()
    return [
        ActualRecord(
            startTime=_utc(r["startTime"]),
            settlementPeriod=r["settlementPeriod"],
            generation_mw=r["generation_mw"],
        )
        for r in rows
    ]
