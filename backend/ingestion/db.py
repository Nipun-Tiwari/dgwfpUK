import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS actuals (
    startTime        TEXT NOT NULL,
    settlementDate   TEXT NOT NULL,
    settlementPeriod INTEGER NOT NULL,
    fuelType         TEXT NOT NULL DEFAULT 'WIND',
    generation_mw    REAL,
    PRIMARY KEY (startTime, settlementPeriod)
);

CREATE TABLE IF NOT EXISTS forecasts (
    startTime     TEXT NOT NULL,
    publishTime   TEXT NOT NULL,
    generation_mw REAL,
    PRIMARY KEY (startTime, publishTime)
);

CREATE TABLE IF NOT EXISTS meta (
    id                    INTEGER PRIMARY KEY,
    ingested_at           TEXT NOT NULL,
    cutoff_definition     TEXT,
    source_urls           TEXT,
    units                 TEXT DEFAULT 'MW',
    timezone_note         TEXT,
    delivery_date_from    TEXT,
    delivery_date_to      TEXT,
    forecast_publish_from TEXT,
    forecast_publish_to   TEXT,
    ingestion_notes       TEXT
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def insert_forecasts(conn: sqlite3.Connection, rows: list[dict]) -> int:
    sql = "INSERT OR REPLACE INTO forecasts (startTime, publishTime, generation_mw) VALUES (?, ?, ?)"
    with conn:
        conn.executemany(
            sql,
            [(r["startTime"], r["publishTime"], r["generation_mw"]) for r in rows],
        )
    return len(rows)


def insert_actuals(conn: sqlite3.Connection, rows: list[dict]) -> int:
    sql = """INSERT OR REPLACE INTO actuals
             (startTime, settlementDate, settlementPeriod, fuelType, generation_mw)
             VALUES (?, ?, ?, 'WIND', ?)"""
    with conn:
        conn.executemany(
            sql,
            [
                (r["startTime"], r["settlementDate"], r["settlementPeriod"], r["generation_mw"])
                for r in rows
            ],
        )
    return len(rows)


def upsert_meta(conn: sqlite3.Connection, meta: dict) -> None:
    conn.execute("DELETE FROM meta")
    conn.execute(
        """INSERT INTO meta
           (ingested_at, cutoff_definition, source_urls, units, timezone_note,
            delivery_date_from, delivery_date_to, forecast_publish_from,
            forecast_publish_to, ingestion_notes)
           VALUES (?, ?, ?, 'MW', ?, ?, ?, ?, ?, ?)""",
        (
            meta["ingested_at"],
            meta.get("cutoff_definition"),
            json.dumps(meta.get("source_urls", [])),
            meta.get("timezone_note"),
            meta.get("delivery_date_from"),
            meta.get("delivery_date_to"),
            meta.get("forecast_publish_from"),
            meta.get("forecast_publish_to"),
            json.dumps(meta.get("ingestion_notes", {})),
        ),
    )
    conn.commit()
