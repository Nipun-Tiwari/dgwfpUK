# Architecture: UK National Wind Forecast Accuracy Dashboard

## 1. System Overview

Three runtime concerns:

1. **One-time ingestion** — fetches historical data from Elexon BMRS, validates it, and writes a populated SQLite store.
2. **FastAPI backend** — reads the bundled store at request time, applies decision-cutoff vintage selection, hourly matching, and metric computation, then serves typed JSON.
3. **React frontend** — typed API client + interactive dashboard (chart, metric cards, interval table, provenance panel).

The backend has **no live dependency on Elexon at request time**. The SQLite store is bundled into the Docker image at build time.

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  One-time Ingestion  (run locally before Docker build)               │
│                                                                      │
│  Elexon BMRS API                                                     │
│  ├─ GET /datasets/FUELHH?fuelType=WIND&settlementDateFrom/To         │
│  └─ GET /datasets/WINDFOR?publishDateTimeFrom/To&pageSize=5000       │
│               │                                                      │
│               ▼                                                      │
│         Pydantic validation → UTC normalization → SQLite store       │
└──────────────────────────────────────────────────────────────────────┘
                          │  (bundled in Docker image)
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                                     │
│                                                                      │
│  repository.py → selection.py → matching.py → analytics.py          │
│                                       │                              │
│                         routes/ (health, meta, metrics, timeseries)  │
└──────────────────────────────────────────────────────────────────────┘
                          │  HTTPS JSON
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  React Frontend  (Vite + TypeScript)                                 │
│                                                                      │
│  api/client.ts → hooks/ → components/                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Layout

```
wind-accuracy-dashboard/
├── backend/
│   ├── ingestion/
│   │   ├── ingest.py           # Fetch + validate + store (idempotent)
│   │   └── verify.py           # Post-ingestion row-count + coverage check
│   ├── data/
│   │   └── wind_data.db        # Populated SQLite store (committed or CI artifact)
│   ├── app/
│   │   ├── main.py             # FastAPI app entry, CORS config
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── meta.py
│   │   │   ├── metrics.py
│   │   │   └── timeseries.py
│   │   ├── repository.py       # SQLite queries, no business logic
│   │   ├── selection.py        # Decision-cutoff vintage selection
│   │   ├── matching.py         # Hourly aggregation + forecast join
│   │   ├── analytics.py        # MAE / RMSE / bias / normalized metrics
│   │   └── schemas.py          # Pydantic request + response models
│   ├── tests/
│   │   ├── fixtures/           # Static JSON fixtures for offline tests
│   │   ├── test_selection.py
│   │   ├── test_matching.py
│   │   ├── test_analytics.py
│   │   ├── test_routes.py
│   │   └── test_ingestion.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.ts
│   │   ├── hooks/
│   │   │   ├── useMetrics.ts
│   │   │   └── useTimeseries.ts
│   │   ├── components/
│   │   │   ├── FilterBar.tsx
│   │   │   ├── ForecastChart.tsx
│   │   │   ├── MetricCards.tsx
│   │   │   ├── IntervalTable.tsx
│   │   │   └── ProvenancePanel.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── tests/
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

---

## 4. Elexon API — Verified Behavior

All facts in this section are based on live API calls made during design. Anything unverified is marked explicitly.

### 4.1 WINDFOR — Historical Vintages

**Endpoint (VERIFIED):** `GET /datasets/WINDFOR`

**Parameters:**
- `publishDateTimeFrom` / `publishDateTimeTo` (ISO-8601 UTC) — selects vintages by publish window
- `pageSize` — raises the default record cap; `pageSize=5000` tested and working
- `format=json`

**Response wrapper (VERIFIED):** `{ "data": [...] }`

**Sample record (VERIFIED):**
```json
{
  "dataset": "WINDFOR",
  "publishTime": "2025-12-31T07:30:00Z",
  "startTime": "2026-01-01T00:00:00Z",
  "generation": 14230
}
```
- `startTime` = start of the 1-hour forecast period (UTC)
- `generation` = forecast value; value range (~5,000–20,000) is consistent with MW scale (VERIFIED by magnitude; no `units` field in response)
- `publishTime` = when this vintage was published

**`/forecast/generation/wind/history` — single-vintage lookup (VERIFIED):**
- Accepts a singular `publishTime` parameter (e.g. `?publishTime=2025-12-31T07:30:00Z`) and returns ~72–74 records for that specific vintage (HTTP 200).
- Returns HTTP 400 when called with `from`/`to` or `publishDateTimeFrom`/`publishDateTimeTo` — date-range forms are not accepted by this endpoint.
- This endpoint cannot enumerate all vintages across a date window; it is not used for bulk ingestion. It can serve as a spot-check tool to verify that a specific known `publishTime` is retrievable.

**`/forecast/generation/wind/evolution` — not usable for bulk ingestion (VERIFIED):**
- Returns HTTP 400 for all date-range query forms tested.

**Record count per day:** Observed 1,260 records for Dec 31, 2025 (8 vintages × ~157 records each); prior research observed 1,008 for a different day — the count varies by day. `pageSize=5000` is sufficient for any single-day query observed so far; see §6.2 for truncation detection.

**Observed publication times for Dec 31, 2025 (VERIFIED):**
```
2025-12-31T02:30:00Z
2025-12-31T04:30:00Z
2025-12-31T07:30:00Z   ← latest eligible for 09:20 UTC cutoff
2025-12-31T09:30:00Z   ← excluded by 09:20 UTC cutoff
2025-12-31T11:30:00Z
2025-12-31T15:30:00Z
2025-12-31T18:30:00Z
2025-12-31T22:30:00Z
```

For a 09:20 UTC cutoff, the latest eligible vintage on Dec 31, 2025 is **`2025-12-31T07:30:00Z`** (VERIFIED). The 09:30 vintage is always excluded under this cutoff. This pattern was also confirmed for Jan 14, 2026. These are observed examples; the publication schedule may vary across other days in January. The cutoff selection algorithm always uses `max(publishTime) ≤ cutoff` independently per hour, so it is robust to schedule variation.

**NOTE on PRD cadence claim:** The PRD states publication cadence at "03:30, 05:30, 08:30, 10:30… GMT." Observed API `publishTime` values show "02:30, 04:30, 07:30, 09:30…" UTC. Since Jan/Dec are both GMT, these values differ. The API-returned `publishTime` is the authoritative value used in all cutoff comparisons; the PRD cadence is treated as approximate background information only.

### 4.2 FUELHH — Actuals

**Endpoint (VERIFIED):** `GET /datasets/FUELHH`

**Parameters:**
- `settlementDateFrom` / `settlementDateTo` (yyyy-MM-dd)
- `fuelType=WIND`
- `format=json`
- Cannot combine `settlementDateFrom/To` with `publishDateTimeFrom/To` — returns HTTP 400 (VERIFIED)

**Response wrapper (VERIFIED):** `{ "data": [...] }`

**Sample record (VERIFIED):**
```json
{
  "dataset": "FUELHH",
  "publishTime": "2026-01-01T23:30:00Z",
  "startTime": "2026-01-01T23:00:00Z",
  "settlementDate": "2026-01-01",
  "settlementPeriod": 47,
  "fuelType": "WIND",
  "generation": 15578
}
```
- `startTime` = start of the 30-min settlement period (UTC)
- `settlementPeriod` = half-hour index 1–48 within the UK settlement day
- `generation` = **UNVERIFIED units** (see §7, Assumption A1). Value range (~10,000–16,000 for Jan 2026) is consistent with MW, but whether it is average MW power or MWh energy is not confirmed from documentation.
- `publishTime` for actuals ≈ 30 min after `startTime` (metering publication lag, not a forecast vintage)

**Records per day (VERIFIED):** 48 per day (one per 30-min settlement period).

---

## 5. Data Model

```sql
-- Two records per delivery hour; generation_mw = NULL means missing (not zero)
CREATE TABLE actuals (
    startTime         TEXT    NOT NULL,  -- UTC ISO-8601, start of 30-min period
    settlementDate    TEXT    NOT NULL,  -- yyyy-MM-dd
    settlementPeriod  INTEGER NOT NULL,  -- 1–48
    fuelType          TEXT    NOT NULL,  -- 'WIND'
    generation_mw     REAL,             -- NULL = missing; units verified before use (see §7 A1)
    PRIMARY KEY (startTime, settlementPeriod)
);

-- All vintages within the ingestion window are retained
CREATE TABLE forecasts (
    startTime     TEXT NOT NULL,  -- UTC ISO-8601, start of 1-hour forecast period
    publishTime   TEXT NOT NULL,  -- UTC ISO-8601, when this vintage was published
    generation_mw REAL,          -- NULL = missing; MW scale verified
    PRIMARY KEY (startTime, publishTime)
);

-- Single row written by ingestion script
CREATE TABLE meta (
    id                    INTEGER PRIMARY KEY,
    ingested_at           TEXT NOT NULL,   -- UTC ISO-8601
    cutoff_definition     TEXT,            -- e.g. 'D-1 09:20 UTC (provisional)'
    source_urls           TEXT,            -- JSON array
    units                 TEXT DEFAULT 'MW',
    timezone_note         TEXT,            -- 'UTC == UK local for Jan 2026 (no DST)'
    delivery_date_from    TEXT,            -- '2026-01-01'
    delivery_date_to      TEXT,            -- '2026-01-31'
    forecast_publish_from TEXT,            -- '2025-12-31T00:00:00Z'
    forecast_publish_to   TEXT             -- '2026-01-31T23:59:59Z'
);
```

`meta` separates delivery-date coverage from forecast-publication-time coverage so the provenance panel can display both accurately.

---

## 6. Ingestion Design

### 6.1 Ingestion Window

| Data | Window |
|---|---|
| FUELHH actuals | `settlementDateFrom=2026-01-01`, `settlementDateTo=2026-01-31` |
| WINDFOR forecasts | `publishDateTimeFrom=2025-12-31T00:00:00Z`, `publishDateTimeTo=2026-01-31T23:59:59Z` |

The forecast window starts on **Dec 31** because delivery day Jan 1 requires the D-1 vintage published on Dec 31. The dashboard only surfaces Jan 2026 delivery dates; the earlier forecast publications are internal data used only for vintage selection.

### 6.2 Pagination Strategy

WINDFOR has a default record cap (~1,000). Query in **per-day `publishDateTimeFrom/To` windows** with `pageSize=5000`. Observed record counts range up to ~1,260/day; `pageSize=5000` provides a comfortable margin.

**Truncation detection:** after each per-day fetch, assert `len(records) < pageSize`. If equal, the response may be silently truncated — log an error and split the window into half-day segments and retry. Never proceed with a potentially truncated fetch.

**Per-day acceptance checks (run during ingestion, logged to `meta`):**
- Assert at least 1 distinct `publishTime` value is present for the day.
- Assert `len(records) < pageSize` (truncation guard above).
- Log the full list of distinct `publishTime` values per day so the publication schedule can be audited post-ingestion.
- Assert that at least one `publishTime ≤ cutoff(D)` exists for every delivery day D; log any day where no eligible vintage was found.

FUELHH: 48 records/day × 31 days = 1,488 records total. Query in **per-week `settlementDateFrom/To` windows** (≤ 336 records/request) to stay safely under any cap.

### 6.3 Transactions and Safe Reruns

All writes use **explicit SQLite transactions**:

- The full ingestion of each per-day batch runs inside a single `BEGIN … COMMIT` block. If any step fails, the transaction rolls back and the database is left in its prior consistent state.
- The overall ingestion uses an outer transaction around schema creation and `meta` row insertion, committed only after all data batches succeed.

**Safe reruns:** ingestion is idempotent via `INSERT OR REPLACE` on primary keys. Running the script twice leaves row counts identical. A rerun of a single day's window replaces only that day's records without touching others.

### 6.4 Duplicate Handling

- **Forecasts**: `INSERT OR REPLACE INTO forecasts` on `PRIMARY KEY (startTime, publishTime)` — the same vintage received twice → last write wins, row count unchanged.
- **Actuals**: `INSERT OR REPLACE INTO actuals` on `PRIMARY KEY (startTime, settlementPeriod)` — same resolution.
- Post-load assertion: query `SELECT COUNT(*) vs COUNT(DISTINCT startTime || publishTime)` to confirm no duplicate primary keys remain.

### 6.5 Malformed Record Handling

- Null or unparseable `generation` → set `generation_mw = NULL`; log row identity (startTime, publishTime/settlementPeriod) at WARNING level.
- Unparseable timestamps → drop row; log at WARNING with row content.
- Missing required fields → drop row; log at WARNING.
- Counts of dropped and retained rows are written to `meta.ingestion_notes` (JSON).

### 6.6 Error Handling

- HTTP 429: exponential backoff, 1 s base, max 5 retries; log each retry.
- HTTP 4xx/5xx (not 429): log URL + params + status; raise; do not fabricate.
- Network timeout: log; raise.

### 6.7 Post-Ingestion Verification

`ingestion/verify.py` checks:
- `actuals` has 48 × 31 = 1,488 rows (one per settlement period per Jan day), or logs the shortfall by date.
- `forecasts` has rows for `startTime` covering every hour of Jan 1–31.
- At least one forecast row exists for each delivery hour with `publishTime ≤ cutoff` where cutoff = D-1 09:20 UTC.
- Exits non-zero if coverage is insufficient.

### 6.8 SQLite Packaging for Production

The populated `wind_data.db` must be present in the Docker build context:

```dockerfile
# backend/Dockerfile
COPY data/wind_data.db /app/data/wind_data.db
```

Workflow:
1. `python -m ingestion.ingest` (runs locally, populates `backend/data/wind_data.db`)
2. `python -m ingestion.verify` (asserts coverage; fails fast if insufficient)
3. Commit `backend/data/wind_data.db` to repo or store as a CI build artifact
4. `docker build` copies the verified database into the image
5. On startup, FastAPI checks that `wind_data.db` exists and `meta` has a row; returns `{ "dataLoaded": false }` from `/health` if not

---

## 7. Decision-Cutoff Logic

### 7.1 Cutoff Definition

```
cutoff(D) = D-1 at HH:MM UTC
```

Configured via env var `DECISION_CUTOFF_TIME` (format `HH:MM`, default `09:20`). This is a **provisional assumption** — it represents an approximate day-ahead decision time, not a regulatory gate-closure time. It is disclosed as provisional in the UI provenance panel and in the README.

**Observed behavior at the default 09:20 UTC cutoff:**
- On Dec 31, 2025 and Jan 14, 2026, the latest eligible publication was `07:30 UTC` (verified).
- The `09:30 UTC` vintage falls after the cutoff and is excluded.
- These are observed examples; the publication schedule is not guaranteed to be identical on every day in January.

### 7.2 Selection Algorithm (per delivery hour)

For each delivery hour `H` on delivery day `D`:

1. Compute `cutoff_dt = datetime(D-1, HH, MM, tzinfo=timezone.utc)` from `DECISION_CUTOFF_TIME`.
2. Filter `forecasts` where `startTime` hour == `H` AND `publishTime <= cutoff_dt`.
3. Among eligible rows, select `argmax(publishTime)`.
4. If no eligible row → hour is incomplete (no forecast available at cutoff).

All `startTime` and `publishTime` values stored in the database are UTC ISO-8601 strings. All comparisons are performed as UTC-aware `datetime` objects (`datetime.fromisoformat(s).replace(tzinfo=timezone.utc)` if not already timezone-aware). No naive datetime objects are used anywhere in the selection or matching pipeline.

This runs identically for both `/api/metrics` and `/api/timeseries`, using the same `cutoff_dt` from the same `DECISION_CUTOFF_TIME` config. The two endpoints cannot disagree.

### 7.3 Provenance Output

`/api/timeseries` returns `selectedPublishTime` per hour — the exact `publishTime` of the forecast used. `/api/meta` and the provenance panel surface the cutoff definition and the range of `selectedPublishTime` values seen in the queried window.

---

## 8. Hourly Matching and Aggregation

### 8.1 Join Key

Delivery hour = UTC `startTime` truncated to the hour.

- WINDFOR rows are hourly (one per `startTime`).
- FUELHH rows are 30-min (two per delivery hour):
  - Period at `H + 00:00` (odd settlementPeriod)
  - Period at `H + 00:30` (even settlementPeriod)

### 8.2 Aggregation Formula

```
actual_mw(H) = mean(generation_mw of the two FUELHH records for hour H)
```

**ASSUMPTION A1 on unit semantics (UNVERIFIED — see §16):** The `generation` field in FUELHH has not been confirmed against authoritative Elexon documentation. Implementation of `matching.py` is **blocked** until A1 is resolved. The aggregation formula above is correct only if `generation` represents average MW power over the 30-min period; a different unit would require a different formula. Do not infer units from numeric magnitude alone.

### 8.3 Completeness Rule

A matched hour is **complete** when ALL of the following hold:
- Both half-hour FUELHH records for that hour have non-null `generation_mw`
- A forecast row was selected (eligible publishTime exists)

Incomplete hours are excluded from all metric calculations.

```
completeness = complete_hours / total_hours_in_window
```

Where `total_hours_in_window` = number of delivery hours in the queried date range (e.g. 744 for January). Both `hoursTotal` and `hoursComplete` are returned in `/api/metrics`.

### 8.4 Completeness and Missing-Interval Counts

Definitions are mutually exclusive and sum to `hoursTotal`:

```
hoursTotal      = number of delivery hours in the queried date range
hoursIncomplete = number of distinct hours that are NOT complete
hoursComplete   = hoursTotal - hoursIncomplete        # invariant: always holds
completeness    = hoursComplete / hoursTotal
```

An hour is incomplete if **either** condition holds:
- No forecast row has `publishTime ≤ cutoff(D)` for that hour (`missingForecast = True`)
- At least one of the two FUELHH half-period records for that hour has null `generation_mw` (`missingActual = True`)

An hour can satisfy both conditions simultaneously; it is still counted once in `hoursIncomplete`.

`/api/metrics` additionally returns the breakdown:
- `hoursMissingForecast` — count of hours where `missingForecast = True` (regardless of actual status)
- `hoursMissingActual` — count of hours where `missingActual = True` (regardless of forecast status)

These two sub-counts may sum to more than `hoursIncomplete` when both conditions hold for the same hour. `hoursComplete + hoursIncomplete = hoursTotal` always holds.

---

## 9. Analytics Formulas

Computed over the set of **complete** matched hours only. All values in MW unless noted.

```
error_mw(H)  = forecast_mw(H) − actual_mw(H)   # positive = over-forecast

MAE          = mean(|error_mw|)
RMSE         = sqrt(mean(error_mw²))
Bias         = mean(error_mw)

mean_actual  = mean(actual_mw) over complete hours
nMAE         = MAE  / mean_actual × 100%         # guarded — see below
nRMSE        = RMSE / mean_actual × 100%         # guarded — see below
```

**Denominator safeguard:** if `mean_actual < NMAE_MIN_ACTUAL_MW` (fixed constant: 100 MW), set `nmae = null` and `nrmse = null`, and set `normalizedOmitted = true` in the response. This is a fixed constant, not configurable via env var.

**No raw MAPE** — excluded because it diverges near-zero and is redundant with nMAE.

---

## 10. API Contracts

All generation values in MW. All timestamps UTC ISO-8601. Error envelope: `{ "error": "code", "message": "..." }`.

### `GET /health`
```json
{ "status": "ok", "dataLoaded": true }
```
Returns `"dataLoaded": false` if `wind_data.db` is absent or `meta` table is empty.

### `GET /api/meta`
```json
{
  "ingestedAt": "<UTC ISO-8601>",
  "cutoff": "D-1 09:20 UTC (provisional — configurable via DECISION_CUTOFF_TIME)",
  "units": "MW",
  "timezoneNote": "UTC == UK local for Jan 2026 (no DST)",
  "sources": ["FUELHH", "WINDFOR"],
  "deliveryDateRange": { "from": "2026-01-01", "to": "2026-01-31" },
  "forecastPublishRange": { "from": "2025-12-31T00:00:00Z", "to": "2026-01-31T23:59:59Z" }
}
```

### `GET /api/metrics?from=YYYY-MM-DD&to=YYYY-MM-DD`

Schema (values are illustrative types, not real data — actual numbers come from the ingested dataset):
```json
{
  "mae": 0.0,
  "rmse": 0.0,
  "bias": 0.0,
  "nmae": 0.0,
  "nrmse": 0.0,
  "normalizedOmitted": false,
  "completeness": 1.0,
  "hoursTotal": 744,
  "hoursComplete": 744,
  "hoursMissingForecast": 0,
  "hoursMissingActual": 0,
  "hoursIncomplete": 0,
  "units": "MW"
}
```
`nmae` and `nrmse` are `null` (JSON null, not a string) when `normalizedOmitted` is `true`.
`hoursComplete + hoursIncomplete == hoursTotal` always holds.

Errors:
```json
400  { "error": "invalid_date_range", "message": "from must be <= to" }
400  { "error": "out_of_range",       "message": "dates must be within 2026-01-01 to 2026-01-31" }
```

### `GET /api/timeseries?from=YYYY-MM-DD&to=YYYY-MM-DD`

Schema (values are illustrative types):
```json
{
  "units": "MW",
  "points": [
    {
      "deliveryHour": "2026-01-01T00:00:00Z",
      "forecast": 0.0,
      "actual": 0.0,
      "error": 0.0,
      "selectedPublishTime": "2025-12-31T07:30:00Z",
      "complete": true
    },
    {
      "deliveryHour": "2026-01-01T01:00:00Z",
      "forecast": null,
      "actual": null,
      "error": null,
      "selectedPublishTime": null,
      "complete": false
    }
  ]
}
```
`forecast`, `actual`, `error`, and `selectedPublishTime` are `null` (JSON null) for incomplete hours.

`/api/metrics` and `/api/timeseries` accept the same `from`/`to` params and use the same cutoff configuration. They cannot disagree.

---

## 11. Component Responsibilities

### `backend/app/repository.py`
- Raw SQL; returns Python dataclasses. No business logic.

### `backend/app/selection.py`
- Applies `cutoff(D)` and `max(publishTime)` per delivery hour.
- Pure function; unit-testable with in-memory fixtures.

### `backend/app/matching.py`
- Aggregates half-hourly FUELHH records to hourly; joins with selected forecasts.
- Returns `list[MatchedHour]` with `complete` flag, `missingForecast` flag, `missingActual` flag.

### `backend/app/analytics.py`
- Accepts `list[MatchedHour]`; returns `MetricsResult`.
- Pure function; no I/O.

### `backend/app/routes/`
- All routes parse params with Pydantic; reject out-of-range dates with 400.
- Consistent error envelope across all routes.
- `metrics` and `timeseries` share the same `cutoff_dt` derivation function.

### Frontend
- `FilterBar` — date/range picker constrained to Jan 2026
- `ForecastChart` — dual-series line chart; hover shows forecast, actual, error
- `MetricCards` — MAE, RMSE, bias, nMAE/nRMSE (or "N/A" when omitted), completeness %
- `IntervalTable` — per-hour rows, sortable by absolute error
- `ProvenancePanel` — cutoff definition (with "provisional" note), `selectedPublishTime` range, units, timezone note, ingestion timestamp, delivery + forecast publish ranges, completeness, data-quality explanation
- All components: explicit **loading / empty / error** states. Never fabricate values.

---

## 12. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| ASGI server | Uvicorn |
| Validation | Pydantic v2 |
| Database | SQLite (`sqlite3` stdlib) |
| Linting/format | Ruff |
| Frontend | React 18 + TypeScript |
| Build | Vite |
| Linting/format | ESLint + Prettier |
| Containerization | Docker + docker-compose (local dev only) |
| Hosting | Render (web service + static site) |
| Backend tests | pytest |
| Frontend tests | Vitest + React Testing Library |

---

## 13. Security and Configuration

| Env var | Default | Purpose |
|---|---|---|
| `FRONTEND_ORIGIN` | (required in production) | CORS allowed origin |
| `DECISION_CUTOFF_TIME` | `09:20` | HH:MM UTC of day-ahead cutoff |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Overridable for testing |

Fixed constants (not env vars):
- `NMAE_MIN_ACTUAL_MW = 100` — denominator safeguard for normalized metrics

CORS is restricted to `FRONTEND_ORIGIN` in production; docker-compose sets it to `http://localhost:5173` for local dev. No secrets in the frontend bundle. HTTPS enforced by Render.

---

## 14. Deployment Topology

```
Internet ──► Render Static Site  (Vite build; BACKEND_URL set at build time)
                     │  HTTPS fetch
                     ▼
              Render Web Service
              └─ Docker image: FastAPI + Uvicorn + /app/data/wind_data.db
```

docker-compose is **local dev only**. Production topology is two separate Render services.

---

## 15. Test Coverage Requirements

| Module | Scenarios |
|---|---|
| `selection.py` | Vintage at exactly cutoff is eligible; vintage 1 s after cutoff is excluded; multiple vintages → `max(publishTime)` selected; no eligible vintage → `complete=False` |
| `matching.py` | Both half-hours present → mean; one half-hour null → `missingActual=True, complete=False`; no forecast → `missingForecast=True, complete=False`; boundary hours 00:00 and 23:00 |
| `analytics.py` | MAE/RMSE/bias match hand-computed golden fixture; nMAE/nRMSE correct; `mean_actual < 100` → `normalizedOmitted=True`; completeness ratio |
| `test_routes.py` | `/api/metrics` and `/api/timeseries` happy path; `from > to` → 400; date outside Jan 2026 → 400; DB absent → 503 or `dataLoaded: false`; metrics and timeseries use same cutoff; `hoursComplete + hoursIncomplete == hoursTotal` in every metrics response |
| `test_ingestion.py` | Malformed row dropped + warned; duplicate forecast rows → single row retained; duplicate actual rows → single row retained; idempotency (two runs = same row counts); truncation detection triggers when `len == pageSize`; per-day distinct publishTime list is logged; at least one eligible vintage exists for every delivery day |
| Frontend | Chart renders from mocked timeseries; cards display mocked metrics; `normalizedOmitted` renders "N/A"; loading/empty/error states; filter change updates request params |

All backend tests use **offline fixtures** (no live Elexon calls in CI).

---

## 16. Unresolved Assumptions

| ID | Assumption | How to validate |
|---|---|---|
| A1 | `FUELHH.generation` is average MW power over the 30-min period (not MWh energy). Aggregation formula depends on this. | Check Elexon BMRS data dictionary / glossary when starting ingestion. Block implementation of `matching.py` until resolved. |
| A2 | All WINDFOR vintages published 2025-12-31 through 2026-01-31 are still retrievable from the API. | Run a test query for each day during ingestion; fail fast if a day returns zero records. |
| A3 | The publication schedule observed on Dec 31, 2025 and Jan 14, 2026 (07:30 UTC as latest eligible under 09:20 cutoff) is representative of all Jan 2026 days. | Inspect actual `publishTime` values for all 31 ingested delivery days; log distinct values. |
| A4 | `pageSize=5000` is sufficient for any single-day WINDFOR query (observed max ~1,008 records/day). | Verify record count < 5,000 for every per-day fetch; log a warning if it equals the pageSize. |
| A5 | 09:20 UTC is an appropriate day-ahead decision cutoff. | Disclosed as provisional in UI and README; not claimed as a regulatory requirement. |
