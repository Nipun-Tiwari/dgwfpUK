# Demo Script — Part 2: Technical Walkthrough (≤ 5 min)

---

## Setup (before recording)

- Have VS Code open on the repo root.
- Have a terminal ready in `wind-accuracy-dashboard/`.
- Have the architecture diagram (or the ARCHITECTURE.md file) ready to reference.
- Have the deployed backend URL open in a browser tab showing the Swagger docs at `/docs`.

---

## Script

### [0:00] Architecture overview

> "Let me walk through how this is built. The system has three layers:
>
> **Ingestion** — a Python script that fetches data from the Elexon BMRS API and writes it to an SQLite
> database bundled inside the backend container.
>
> **Backend** — a FastAPI application that reads the database and exposes four HTTP endpoints:
> `/health`, `/api/meta`, `/api/metrics`, and `/api/timeseries`.
>
> **Frontend** — a React single-page app built with Vite and Recharts, deployed as a static site.
>
> There's no live data pipeline — data is fetched once, stored in SQLite, and shipped inside the Docker
> image. That's a deliberate simplicity tradeoff for this prototype."

*[Show the directory tree in the terminal or VS Code explorer.]*

---

### [0:45] Ingestion and SQLite bundling

> "Ingestion fetches WINDFOR forecasts from December 31 (because the cutoff for January 1 is the
> morning of December 31) through January 31, and FUELHH actuals for all of January.
>
> Each WINDFOR day is fetched in a single request with `pageSize=5000`. If we ever get exactly 5,000
> records back, we log an ERROR and split into two half-day batches — that's the truncation guard.
>
> Everything is written in a single `BEGIN … COMMIT` transaction per batch. `INSERT OR REPLACE` makes
> it idempotent — running ingestion twice produces the same database."

*[Open `backend/ingestion/ingest.py` and point to the truncation guard and transaction code.]*

> "After ingestion, `verify.py` checks that all 744 delivery hours in January 2026 have an eligible
> forecast vintage. It exits non-zero with a coverage report if any are missing."

---

### [1:30] Cutoff selection and data-leakage prevention

> "This is the most important correctness property of the system: we must never use a forecast
> that was published *after* the decision was made.
>
> `selection.py` implements this. For a delivery hour H on delivery day D, the cutoff is
> D-minus-1 at 09:20 UTC. We take the maximum `publishTime` across all WINDFOR vintages for H that
> satisfies `publishTime ≤ cutoff_dt`."

*[Open `backend/app/selection.py`.]*

> "All comparisons use UTC-aware `datetime` objects — there are no naive datetime comparisons anywhere.
> Test coverage includes the Jan 1 boundary case: a Dec 31 vintage at 07:30 UTC is eligible for
> Jan 1 delivery."

---

### [2:00] Hourly matching and unit semantics (A1)

> "The FUELHH API returns half-hourly data. To match against the hourly WINDFOR forecast, we average
> the two half-hours:
>
>   `actual_mw(H) = mean(generation at H+00:00, generation at H+00:30)`
>
> This is the A1 decision. `generation` in FUELHH is average MW power over the settlement period,
> not MWh energy. If it were MWh, values of 10–16 thousand would imply 20–32 GW instantaneous power —
> above total UK installed wind capacity. The MW interpretation is physically consistent."

*[Open `backend/app/matching.py`.]*

> "If either half-hour is missing, `actual_mw` is `None` — never zero. If no eligible vintage exists,
> `forecast_mw` is `None`. Hours with any null field are `complete=False` and excluded from metrics."

---

### [2:45] Metric formulas

> "Four metrics:
>
> - MAE: mean of |forecast − actual| across complete hours
> - RMSE: square root of mean squared error
> - Bias: mean of (forecast − actual) — positive means systematic overestimate
> - nMAE and nRMSE: MAE and RMSE divided by mean actual, as a percentage
>
> Normalised metrics are `null` (not zero) when mean actual is below 100 MW — that threshold prevents
> meaningless percentage figures during near-zero-wind periods."

*[Open `backend/app/analytics.py`.]*

---

### [3:15] API contracts and tests

> "The four routes are thin wrappers around the domain logic. `/api/metrics` and `/api/timeseries`
> use the same `cutoff_for_delivery_day` function, so they always agree on which forecasts are eligible
> for a given window.
>
> 37 backend tests, all offline using recorded fixtures — no live API calls in CI. 5 frontend tests
> with Vitest and mocked fetch responses."

*[Run `python -m pytest backend/tests/` in the terminal — all pass.]*

---

### [3:45] Docker and Render deployment

> "The backend Dockerfile is based on `python:3.12-slim`. It copies `data/wind_data.db` into the image
> at build time — if the file is absent, the Docker build fails explicitly. On startup, FastAPI checks
> that the database is loaded; if not, `/health` returns `dataLoaded: false` and all data routes return
> 503 — so the container never crash-loops on Render's health check.
>
> The frontend Dockerfile is a two-stage build: `node:20-slim` builds the Vite app with
> `VITE_BACKEND_URL` baked in as a build arg, then `nginx:alpine` serves the dist folder. Nginx is
> configured to rewrite all paths to `index.html` for React Router."

*[Show `backend/Dockerfile` and `frontend/Dockerfile` briefly.]*

> "A `render.yaml` blueprint provisions both services. The key post-deploy step is setting
> `FRONTEND_ORIGIN` on the backend to the exact static site URL — without that, CORS blocks all API
> calls from the browser."

---

### [4:30] Summary

> "To summarise: ingestion → SQLite → FastAPI → React, all containerised with Docker and deployed to
> Render. The whole system can be stood up locally with a single `docker compose up`, and the full
> test suite runs offline in under five seconds.
>
> The deliberate design choices — no zero-imputation, explicit incomplete-hour marking, provenance
> panel showing the cutoff and its provisional nature — make the accuracy claims auditable and honest."

---

*[End of Part 2 — target: ~5 minutes]*
