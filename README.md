# UK National Wind Forecast Accuracy Dashboard

> **Procurement-scope disclaimer:** This dashboard is a prototype built as a skills assessment. It is not
> affiliated with, endorsed by, or validated by any electricity system operator, balancing authority, or
> official data provider. All data is sourced from the publicly available Elexon BMRS API. Metrics are
> computed with best-effort accuracy but should not be used for commercial, operational, or procurement
> decisions without independent verification.

A single-page analytical dashboard that compares Elexon WINDFOR day-ahead wind generation forecasts against
FUELHH half-hourly actuals for January 2026. It quantifies forecast accuracy (MAE, RMSE, bias, nMAE, nRMSE)
using a fixed decision-time cutoff (09:20 UTC the day before delivery, **provisional**) and exposes the
results through a FastAPI backend and a React/Recharts frontend.

---

## Live Deployment

| Service | URL |
|---|---|
| Backend API | *(set after Render deploy — update this line)* |
| Frontend dashboard | *(set after Render deploy — update this line)* |

---

## Repository structure

```
wind-accuracy-dashboard/
├── backend/
│   ├── ingestion/           # Data fetch, validation, SQLite storage
│   │   ├── elexon_client.py # HTTP fetch with exponential backoff (httpx)
│   │   ├── models.py        # Pydantic validation models for WINDFOR + FUELHH
│   │   ├── db.py            # SQLite schema + insert functions
│   │   ├── ingest.py        # Main ingestion orchestrator
│   │   └── verify.py        # Post-ingestion coverage check
│   ├── data/
│   │   └── wind_data.db     # SQLite DB (built by ingestion; committed to repo)
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS middleware, router registration
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── repository.py    # Raw SQL queries (no business logic)
│   │   ├── selection.py     # Decision-cutoff vintage selection (pure functions)
│   │   ├── matching.py      # Hourly aggregation + forecast join (pure functions)
│   │   ├── analytics.py     # MAE/RMSE/bias/nMAE/nRMSE computation (pure functions)
│   │   └── routes/          # FastAPI routers: health, meta, metrics, timeseries
│   ├── tests/               # pytest test suite (37 tests, all offline)
│   ├── pyproject.toml       # Ruff config + pytest asyncio_mode=auto
│   ├── requirements.txt     # Pinned Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # TypeScript types + typed fetch wrapper
│   │   ├── hooks/           # useMetrics, useTimeseries (AbortController stale-cancel)
│   │   ├── components/      # FilterBar, ForecastChart, MetricCards, IntervalTable, ProvenancePanel
│   │   ├── App.tsx          # Dashboard layout + persistent disclaimer
│   │   └── main.tsx
│   ├── tests/               # Vitest component tests
│   ├── nginx.conf           # SPA rewrite rule for nginx serve stage
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── render.yaml              # Render deployment blueprint
├── .env.example             # All environment variables with defaults
├── decisions.md             # Architecture decision records
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── TASKS.md
└── HANDOFF.md               # Handoff notes for continuing agents
```

---

## Local setup — Docker (recommended)

**Prerequisites:** Docker Desktop running, `wind_data.db` already built (see Ingestion below).

```bash
# From the repo root:
docker compose up
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Health check: http://localhost:8000/health

> **Note:** `backend/data/wind_data.db` must exist before building the Docker image.
> The backend Dockerfile will fail explicitly if the file is absent from the build context.

---

## Local setup — Non-Docker

### Backend

```bash
cd wind-accuracy-dashboard/
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --app-dir .
```

### Frontend

```bash
cd wind-accuracy-dashboard/frontend/
npm install
npm run dev
```

The frontend dev server reads `VITE_BACKEND_URL` from a `.env` file (or env var). Create
`frontend/.env` with:

```
VITE_BACKEND_URL=http://localhost:8000
```

---

## Ingestion

Run ingestion **before** building the Docker image or running the backend for the first time.

```bash
# From wind-accuracy-dashboard/
python -m backend.ingestion.ingest
python -m backend.ingestion.verify
```

`ingest.py` fetches WINDFOR forecasts (2025-12-31 to 2026-01-31) and FUELHH actuals (January 2026)
from the Elexon BMRS API and writes them to `backend/data/wind_data.db`.

`verify.py` exits 0 on success and prints a coverage report. It exits non-zero if any delivery hour
in January 2026 lacks an eligible forecast vintage.

---

## Tests

```bash
# Backend (37 tests, all offline via fixtures)
python -m pytest backend/tests/

# Frontend (Vitest)
cd frontend && npm run test
```

---

## Environment variables

| Variable | Default | Required in prod | Description |
|---|---|---|---|
| `WIND_DB_PATH` | `backend/data/wind_data.db` | Yes | Path to SQLite DB inside the container |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | **Yes** | Exact frontend origin for CORS allow-list |
| `DECISION_CUTOFF_TIME` | `09:20` | No | HH:MM UTC cutoff for forecast vintage selection |
| `VITE_BACKEND_URL` | `http://localhost:8000` | **Yes** | Backend URL baked into the frontend at build time |

> **CORS:** `FRONTEND_ORIGIN` must match the exact scheme + host + port of the frontend with **no trailing slash**.
> Setting an incorrect value causes all API calls to fail with a CORS error in the browser console.

---

## Timezone assumption

All timestamps are stored and processed in **UTC**. January 2026 falls outside British Summer Time (BST),
so UTC == UK local time for the entire analysis window — there is no DST ambiguity.

`DECISION_CUTOFF_TIME` (default `09:20`) is **provisional**: the PRD specifies approximate publication
cadences and the Elexon API returned publish times of `02:30, 04:30, 07:30, 09:30 UTC` in practice.
The vintage selection logic uses `max(publishTime) ≤ cutoff_dt` which is robust to timing variations.

---

## FUELHH unit assumption (A1)

**Status:** Resolved by physical plausibility analysis.

FUELHH `generation` values for January 2026 range from approximately 10,000–16,000. If these were
interpreted as MWh energy over a 30-minute settlement period, the implied instantaneous power would be
20,000–32,000 MW, exceeding total UK installed wind capacity (~25 GW). The **average MW power**
interpretation (values of 10,000–16,000 MW) is consistent with UK installed capacity.

**Aggregation formula:**
```
actual_mw(H) = mean(generation_mw at H+00:00, generation_mw at H+00:30)
```

Both FUELHH actuals and WINDFOR forecasts are therefore in the same unit (MW), and no conversion is
required before computing errors.

**Note:** Official Elexon BMRS documentation for the FUELHH endpoint was inaccessible during design.
This assumption is stated explicitly in the `/api/meta` endpoint response and the Provenance Panel.

---

## Data quality notes

- **Completeness:** A delivery hour is "complete" when both its FUELHH half-hours have non-null
  `generation_mw` values and an eligible WINDFOR vintage exists at or before the decision cutoff.
- **Missing records:** Missing actuals or forecasts are represented as `null` in the API response,
  never as zero. Incomplete hours are excluded from metric numerators and denominators.
- **No zero-imputation:** A genuine `actual_mw = 0.0` (e.g. zero wind generation) is treated as a
  valid complete data point and included in metrics — it is not confused with a missing value.
- **Idempotency:** Re-running ingestion produces the same row counts (`INSERT OR REPLACE`).

---

## Deployment to Render

See [`render.yaml`](render.yaml) for the full deployment blueprint. Summary:

1. Commit `backend/data/wind_data.db` to the repo (or Git LFS if > 100 MB).
2. Push repo to GitHub.
3. In Render dashboard → New → Blueprint → select `render.yaml`.
4. After first deploy, note the backend web service URL and set `FRONTEND_ORIGIN` on the backend service
   to the exact static site URL (no trailing slash). Re-deploy the backend.
5. Confirm `/health` returns `{"status":"ok","dataLoaded":true}` over HTTPS.

**Cold start note:** The Render free tier sleeps after ~15 minutes of inactivity. The first request
after sleep takes ~15–30 seconds. Upgrade to a paid instance tier if this is unacceptable for a live demo.

---

## AI tool usage disclosure

This project was built with the assistance of AI coding tools (Google Antigravity / Gemini). AI tools
were used for:

- Scaffolding boilerplate (Dockerfiles, configs, test structure)
- Code review and linting suggestions
- Drafting documentation

All data pipeline logic, metric formulas, architectural decisions (including the A1 unit assumption),
and test coverage were reviewed and validated by the author. AI-generated code was not used without
understanding and verifying its correctness.

The HANDOFF.md file in this repository was written to enable AI-assisted continuation of implementation
across sessions, following the project's documented task plan.
