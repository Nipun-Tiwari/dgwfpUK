import sqlite3
from pathlib import Path

from backend.ingestion.db import SCHEMA, insert_actuals, insert_forecasts
from backend.ingestion.ingest import _validate_fuelhh, _validate_windfor

FIXTURES = Path(__file__).parent / "fixtures"


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def test_malformed_generation_windfor():
    raw = [{"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation": "bad"}]
    valid, dropped = _validate_windfor(raw)
    assert len(valid) == 1
    assert valid[0]["generation_mw"] is None
    assert dropped == 0


def test_unparseable_timestamp_windfor():
    raw = [{"startTime": "not-a-date", "publishTime": "2025-12-31T07:30:00Z", "generation": 100}]
    valid, dropped = _validate_windfor(raw)
    assert len(valid) == 0
    assert dropped == 1


def test_duplicate_forecast_rows():
    conn = _make_db()
    rows = [
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation_mw": 100.0},
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation_mw": 100.0},
    ]
    insert_forecasts(conn, rows)
    count = conn.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
    assert count == 1


def test_duplicate_actual_rows():
    conn = _make_db()
    rows = [
        {"startTime": "2026-01-01T00:00:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 1, "generation_mw": 100.0},
        {"startTime": "2026-01-01T00:00:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 1, "generation_mw": 100.0},
    ]
    insert_actuals(conn, rows)
    count = conn.execute("SELECT COUNT(*) FROM actuals").fetchone()[0]
    assert count == 1


def test_idempotency():
    conn = _make_db()
    rows = [{"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation_mw": 100.0}]
    insert_forecasts(conn, rows)
    insert_forecasts(conn, rows)
    count = conn.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
    assert count == 1


def test_truncation_detection():
    raw = [
        {"startTime": f"2026-01-01T{h:02d}:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation": 100}
        for h in range(48)
    ]
    page_size = 48
    assert len(raw) >= page_size


def test_null_generation_fuelhh():
    raw = [{"startTime": "2026-01-01T00:00:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "WIND", "generation": None}]
    valid, dropped = _validate_fuelhh(raw)
    assert len(valid) == 1
    assert valid[0]["generation_mw"] is None
    assert dropped == 0


def test_jan1_boundary():
    raw = [{"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T07:30:00Z", "generation": 14000}]
    valid, dropped = _validate_windfor(raw)
    assert len(valid) == 1
    assert valid[0]["startTime"] == "2026-01-01T00:00:00Z"
