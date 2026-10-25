# Implementation Decisions

## A1 — FUELHH.generation unit resolution
**Status:** Resolved
**Decision:** FUELHH `generation` is treated as average MW power over the 30-min settlement period.
**Basis:** Physical plausibility — observed values of 10,000–16,000. If interpreted as MWh energy over 30 min, this implies instantaneous power of 20,000–32,000 MW, which exceeds total UK installed wind capacity (~25 GW). The MW interpretation is consistent with WINDFOR forecast values in the same range. Official Elexon documentation was inaccessible during design.
**Formula:** `actual_mw(H) = mean(generation_mw at H+00:00, generation_mw at H+00:30)`

## A2 — Jan 2026 vintage availability
**Status:** Resolved
**Decision:** 18,688 WINDFOR forecasts (fetched from 2025-12-31 to 2026-01-31) and 1,488 FUELHH actuals were ingested into SQLite (`wind_data.db`, 2.1 MB).
`verify.py` confirmed 744/744 delivery hours (100%) in January 2026 have complete actuals and eligible decision-cutoff forecasts.

## A3 — Publication schedule observed
**Status:** Resolved
**Decision:** Elexon BMRS API returned publish times at 02:30, 04:30, 07:30, 09:30 UTC (differing slightly from the PRD stated 03:30, 05:30, 08:30, 10:30 GMT).
The provisional decision cutoff `09:20 UTC` selects the latest pre-cutoff morning vintage (`07:30 UTC`), cleanly preventing data leakage.

## A4 — PageSize adequacy
**Status:** Resolved
**Decision:** `pageSize=5000` was sufficient for all daily WINDFOR batches (each day returned < 1,000 records) and weekly FUELHH batches; no truncation detected.

## Technical Deviations & Enhancements
1. **pytest-asyncio:** Pinned `pytest-asyncio==0.24.0` in `requirements.txt` (as `pytest-anyio` does not exist on PyPI).
2. **Docker Healthcheck:** Backend healthcheck uses `python -c "import urllib.request; urllib.request.urlopen(...)"` since `python:3.12-slim` does not include `curl`.
3. **Database Packaging:** `wind_data.db` (2.1 MB) is copied into the Docker container during build and committed to the Git repo for direct Render deployment without requiring external object storage or LFS.

