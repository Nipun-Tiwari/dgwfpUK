"""Verify ingested data coverage. Exits non-zero on insufficient coverage."""

import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.getenv("WIND_DB_PATH", str(Path(__file__).parent.parent / "data" / "wind_data.db"))
CUTOFF_TIME = os.getenv("DECISION_CUTOFF_TIME", "09:20")
DELIVERY_FROM = date(2026, 1, 1)
DELIVERY_TO = date(2026, 1, 31)


def parse_cutoff(cutoff_str: str, delivery_day: date) -> datetime:
    h, m = map(int, cutoff_str.split(":"))
    prev = delivery_day - timedelta(days=1)
    return datetime(prev.year, prev.month, prev.day, h, m, 0, tzinfo=timezone.utc)


def main() -> int:
    if not Path(DB_PATH).exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    actual_count = conn.execute("SELECT COUNT(*) FROM actuals").fetchone()[0]
    forecast_count = conn.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]

    print(f"actuals:   {actual_count} rows  (expected 1488 = 48 per day x 31 days)")
    print(f"forecasts: {forecast_count} rows")

    missing_actual_dates = []
    current = DELIVERY_FROM
    while current <= DELIVERY_TO:
        count = conn.execute(
            "SELECT COUNT(*) FROM actuals WHERE settlementDate = ?", (str(current),)
        ).fetchone()[0]
        if count < 48:
            missing_actual_dates.append((str(current), count))
        current += timedelta(days=1)

    if missing_actual_dates:
        print(f"WARNING: missing/incomplete actuals for {len(missing_actual_dates)} days:")
        for d, c in missing_actual_dates:
            print(f"  {d}: {c}/48 records")

    total_hours = 0
    missing_eligible: list[str] = []
    current = DELIVERY_FROM
    while current <= DELIVERY_TO:
        cutoff_dt = parse_cutoff(CUTOFF_TIME, current)
        cutoff_str = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        for hour in range(24):
            hour_start = datetime(current.year, current.month, current.day, hour, 0, 0, tzinfo=timezone.utc)
            hour_str = hour_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            total_hours += 1
            count = conn.execute(
                "SELECT COUNT(*) FROM forecasts WHERE startTime = ? AND publishTime <= ?",
                (hour_str, cutoff_str),
            ).fetchone()[0]
            if count == 0:
                missing_eligible.append(hour_str)
        current += timedelta(days=1)

    eligible_covered = total_hours - len(missing_eligible)
    print(f"eligible:  {eligible_covered}/{total_hours} delivery hours have a forecast at cutoff")
    if missing_eligible:
        print(f"missing_eligible: {missing_eligible[:10]}{'...' if len(missing_eligible) > 10 else ''}")

    meta_row = conn.execute("SELECT ingestion_notes FROM meta").fetchone()
    if meta_row and meta_row[0]:
        notes = json.loads(meta_row[0])
        per_day = notes.get("windfor_per_day", {})
        single_vintage_days = [d for d, pts in per_day.items() if len(pts) == 1]
        page_warnings = notes.get("page_size_warnings", 0)
        dropped_dup = notes.get("windfor_dropped", 0) + notes.get("fuelhh_dropped", 0)
        print(f"page_size_warnings: {page_warnings}")
        print(f"single_vintage_days: {single_vintage_days}")
        print(f"duplicate_records_dropped: {dropped_dup}")
        print("distinct publishTimes per day: (see ingestion_notes in meta table)")

    conn.close()

    ok = actual_count >= 1488 and len(missing_eligible) == 0
    if not ok:
        print("\nVERIFICATION FAILED", file=sys.stderr)
        return 1
    print("\nVERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
