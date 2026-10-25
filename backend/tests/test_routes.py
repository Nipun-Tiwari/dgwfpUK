import sqlite3
from unittest.mock import patch

import pytest
from backend.app.main import app
from backend.ingestion.db import SCHEMA
from fastapi.testclient import TestClient


def _make_test_db(path: str):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        """INSERT INTO meta (ingested_at, cutoff_definition, source_urls, units, timezone_note,
           delivery_date_from, delivery_date_to, forecast_publish_from, forecast_publish_to)
           VALUES (?, ?, ?, 'MW', 'UTC == UK local for Jan 2026', '2026-01-01', '2026-01-31',
           '2025-12-31T00:00:00Z', '2026-01-31T23:59:59Z')""",
        ("2026-01-31T12:00:00Z", "D-1 09:20 UTC (provisional)", '["FUELHH", "WINDFOR"]'),
    )
    conn.execute(
        "INSERT INTO forecasts (startTime, publishTime, generation_mw) VALUES (?, ?, ?)",
        ("2026-01-01T00:00:00Z", "2025-12-31T07:30:00Z", 14000.0),
    )
    conn.execute(
        "INSERT INTO actuals (startTime, settlementDate, settlementPeriod, fuelType, generation_mw) VALUES (?, ?, ?, 'WIND', ?)",
        ("2026-01-01T00:00:00Z", "2026-01-01", 1, 15000.0),
    )
    conn.execute(
        "INSERT INTO actuals (startTime, settlementDate, settlementPeriod, fuelType, generation_mw) VALUES (?, ?, ?, 'WIND', ?)",
        ("2026-01-01T00:30:00Z", "2026-01-01", 2, 15200.0),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client_with_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    _make_test_db(db_path)
    with patch("backend.app.repository.DB_PATH", db_path):
        with TestClient(app) as client:
            yield client


@pytest.fixture
def client_no_db(tmp_path):
    db_path = str(tmp_path / "missing.db")
    with patch("backend.app.repository.DB_PATH", db_path):
        with TestClient(app) as client:
            yield client


def test_health_ok(client_with_db):
    resp = client_with_db.get("/health")
    assert resp.status_code == 200
    assert resp.json()["dataLoaded"] is True


def test_health_no_db(client_no_db):
    resp = client_no_db.get("/health")
    assert resp.status_code == 200
    assert resp.json()["dataLoaded"] is False


def test_meta_ok(client_with_db):
    resp = client_with_db.get("/api/meta")
    assert resp.status_code == 200
    assert "ingestedAt" in resp.json()


def test_metrics_503_no_db(client_no_db):
    resp = client_no_db.get("/api/metrics?from=2026-01-01&to=2026-01-01")
    assert resp.status_code == 503


def test_metrics_400_from_gt_to(client_with_db):
    resp = client_with_db.get("/api/metrics?from=2026-01-10&to=2026-01-01")
    assert resp.status_code == 400


def test_metrics_400_out_of_range(client_with_db):
    resp = client_with_db.get("/api/metrics?from=2025-12-01&to=2025-12-31")
    assert resp.status_code == 400


def test_metrics_happy_path(client_with_db):
    resp = client_with_db.get("/api/metrics?from=2026-01-01&to=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hoursComplete"] + data["hoursIncomplete"] == data["hoursTotal"]


def test_timeseries_happy_path(client_with_db):
    resp = client_with_db.get("/api/timeseries?from=2026-01-01&to=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert len(data["points"]) == 24


def test_metrics_timeseries_same_cutoff(client_with_db):
    m = client_with_db.get("/api/metrics?from=2026-01-01&to=2026-01-01").json()
    ts = client_with_db.get("/api/timeseries?from=2026-01-01&to=2026-01-01").json()
    complete_from_ts = sum(1 for p in ts["points"] if p["complete"])
    assert m["hoursComplete"] == complete_from_ts
