# Handoff Notes for Continuing Implementation (T6–T9)

This file captures everything the implementing AI needs to know that is not already in
`docs/IMPLEMENTATION_PLAN.md`, `docs/ARCHITECTURE.md`, or `docs/TASKS.md`.

---

## What has been completed

T0 through T5 are fully implemented and all tests pass:

- **Backend:** 37/37 pytest tests pass, Ruff lint clean
- **Frontend:** 5/5 Vitest tests pass

All code lives in `wind-accuracy-dashboard/`.

---

## Canonical commands (run from `wind-accuracy-dashboard/`)

| Action | Command |
|---|---|
| Start backend (dev) | `uvicorn backend.app.main:app --reload --app-dir .` |
| Run backend tests | `python -m pytest backend/tests/` |
| Run ingestion | `python -m backend.ingestion.ingest` |
| Run ingestion verify | `python -m backend.ingestion.verify` |
| Backend lint | `python -m ruff check backend/` |
| Start frontend (dev) | `cd frontend && npm run dev` |
| Run frontend tests | `cd frontend && npm run test` |

---

## Known deviations from the docs (important)

### 1. `pytest-anyio` does not exist
`requirements.txt` uses `pytest-asyncio==0.24.0` instead. Do not change this.

### 2. Golden fixture RMSE
`backend/tests/fixtures/golden_metrics.json` uses the Python-computed value `841.2639300481152`
and `nrmse: 6.185764191530259`. The hand-computed approximation in the IMPLEMENTATION_PLAN
(`841.264157`) was slightly off due to rounding. Do not change the fixture.

### 3. Observed Elexon publishTime values differ from PRD
The PRD states publication cadence at `03:30, 05:30, 08:30, 10:30 GMT`.
Actual API-returned `publishTime` values observed are `02:30, 04:30, 07:30, 09:30 UTC`.
The code uses `max(publishTime) <= cutoff` so it is robust to this — no code change needed,
but be aware when writing README or documentation.

### 4. DECISION_CUTOFF_TIME is hardcoded in routes (known gap)
`backend/app/routes/metrics.py` and `backend/app/routes/timeseries.py` both have:
```python
CUTOFF_TIME = "09:20"
```
This should read from the environment variable `DECISION_CUTOFF_TIME` (default `"09:20"`).
Fix this in T6 when wiring env vars in Docker:
```python
import os
CUTOFF_TIME = os.getenv("DECISION_CUTOFF_TIME", "09:20")
```

---

## Directory layout as built

```
wind-accuracy-dashboard/
├── backend/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── elexon_client.py     # HTTP fetch with exponential backoff (httpx)
│   │   ├── models.py            # Pydantic validation models for WINDFOR + FUELHH
│   │   ├── db.py                # SQLite schema + insert functions
│   │   ├── ingest.py            # Main ingestion orchestrator (run with python -m)
│   │   └── verify.py            # Post-ingestion coverage check (run with python -m)
│   ├── data/
│   │   └── .gitkeep             # wind_data.db goes here after ingestion
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS middleware, router registration
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── repository.py        # Raw SQL queries, returns dataclasses, no business logic
│   │   ├── selection.py         # Decision-cutoff vintage selection (pure functions)
│   │   ├── matching.py          # Hourly aggregation + forecast join (pure functions)
│   │   ├── analytics.py         # MAE/RMSE/bias/nMAE/nRMSE computation (pure functions)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py        # GET /health
│   │       ├── meta.py          # GET /api/meta
│   │       ├── metrics.py       # GET /api/metrics?from=&to=
│   │       └── timeseries.py    # GET /api/timeseries?from=&to=
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── fixtures/
│   │   │   ├── windfor_sample.json
│   │   │   ├── fuelhh_sample.json
│   │   │   └── golden_metrics.json
│   │   ├── test_ingestion.py
│   │   ├── test_selection.py
│   │   ├── test_matching.py
│   │   ├── test_analytics.py
│   │   └── test_routes.py
│   ├── pyproject.toml           # Ruff config + pytest asyncio_mode=auto
│   └── requirements.txt         # Pinned deps (no pytest-anyio — use pytest-asyncio)
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── types.ts         # TypeScript interfaces matching backend Pydantic schemas
│   │   │   └── client.ts        # Typed fetch wrapper; reads VITE_BACKEND_URL
│   │   ├── hooks/
│   │   │   ├── useMetrics.ts    # useMetrics(from, to) -> {data, loading, error}
│   │   │   └── useTimeseries.ts # useTimeseries(from, to) -> {data, loading, error}
│   │   ├── components/
│   │   │   ├── FilterBar.tsx
│   │   │   ├── ForecastChart.tsx   # Recharts dual-series line chart
│   │   │   ├── MetricCards.tsx
│   │   │   ├── IntervalTable.tsx   # Sortable by absolute error
│   │   │   └── ProvenancePanel.tsx
│   │   ├── App.tsx              # Full dashboard layout with persistent disclaimer
│   │   └── main.tsx
│   ├── tests/
│   │   ├── setup.ts
│   │   ├── client.test.ts
│   │   └── App.test.tsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── .eslintrc.cjs
│   └── .prettierrc
├── decisions.md                 # A1 resolution (FUELHH generation = avg MW power)
├── .gitignore
└── HANDOFF.md                   # This file
```

---

## Key architectural decisions already made

- **FUELHH.generation is average MW power** (not MWh). `actual_mw(H) = mean(H+00:00, H+00:30)`.
  Basis: physical plausibility. Documented in `decisions.md` and `app/routes/meta.py`.
- **SQLite** for storage; `wind_data.db` must be built locally before Docker image is built.
- **WINDFOR fetch window starts Dec 31** because Jan 1 delivery requires Dec 31 vintages.
- **Frontend uses Recharts** for the forecast-vs-actual line chart.
- **`VITE_BACKEND_URL`** is a build-time Vite env var (baked in at `npm run build`), not runtime.
  The frontend Dockerfile must pass it as a build arg.
- **CORS**: `FRONTEND_ORIGIN` env var controls allowed origin. Never use `allow_origins=["*"]`
  in production.

---

## What T6–T9 need to do

### T6 — Docker + docker-compose

Files to create:
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.env.example`

**Before building the Docker image**, run ingestion to populate `backend/data/wind_data.db`:
```
python -m backend.ingestion.ingest
python -m backend.ingestion.verify
```

**backend/Dockerfile** (key points):
- Base: `python:3.12-slim`
- Copy `data/wind_data.db` into the image — build FAILS explicitly if absent
- Run with `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- Set env vars: `WIND_DB_PATH`, `FRONTEND_ORIGIN`, `DECISION_CUTOFF_TIME`

**frontend/Dockerfile** (key points):
- Build stage: `node:20-slim`, pass `VITE_BACKEND_URL` as a build ARG
- Serve stage: `nginx:alpine` serving `dist/`
- Must configure nginx to rewrite all paths to `index.html` (for React Router / SPA)

**docker-compose.yml**:
- Backend on port 8000, frontend on port 5173 (or 80)
- `FRONTEND_ORIGIN=http://localhost:5173`
- `VITE_BACKEND_URL=http://localhost:8000`

**Fix `DECISION_CUTOFF_TIME` env var gap** (see deviation #4 above):
In `backend/app/routes/metrics.py` and `backend/app/routes/timeseries.py`, change:
```python
CUTOFF_TIME = "09:20"
```
to:
```python
import os
CUTOFF_TIME = os.getenv("DECISION_CUTOFF_TIME", "09:20")
```

### T7 — Deploy to Render

See `docs/IMPLEMENTATION_PLAN.md` T7 section. Key points:
- Render Web Service from `backend/Dockerfile`
- Render Static Site from `frontend/` with `VITE_BACKEND_URL` set to backend URL
- Set `FRONTEND_ORIGIN` on backend to exact static site origin (no trailing slash)
- Health check path: `/health`
- Rewrite rules on static site: all paths → `index.html`
- `wind_data.db` must be committed to repo (or added as Git LFS if > 100 MB)

### T8 — README

See `docs/IMPLEMENTATION_PLAN.md` T8 section. Required sections listed there.
Include the A1 resolution (FUELHH unit assumption) from `decisions.md`.

### T9 — Demo

See `docs/IMPLEMENTATION_PLAN.md` T9 section for the two-part script outline.

---

## Environment variables reference

| Var | Default | Where used |
|---|---|---|
| `WIND_DB_PATH` | `backend/data/wind_data.db` | `repository.py`, `ingest.py`, `verify.py` |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | `main.py` CORS middleware |
| `DECISION_CUTOFF_TIME` | `09:20` | `ingest.py`, `routes/metrics.py`, `routes/timeseries.py` |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | `ingest.py` |
| `VITE_BACKEND_URL` | `http://localhost:8000` | `frontend/src/api/client.ts` (build-time) |
