# Implementation Plan: UK National Wind Forecast Accuracy Dashboard

Tasks follow the PRD dependency order. Complete each task fully before starting the next; the app must remain runnable after every milestone.

**A1 resolved — no hard blocks remaining.** `FUELHH.generation` is confirmed as average MW power over the 30-min period (MWh interpretation is physically impossible against UK installed capacity). All modules may be implemented in order. Frontend component work (T4/T5) may proceed in parallel with T2/T3 using clearly labelled static fixtures; switch to live data once T3 is complete.

---

## T0 — Scaffold Monorepo

**Objective:** Empty but runnable apps with linting, formatting, and dependency pinning in place.

**Repository root:** `wind-accuracy-dashboard/`  
All commands below are run from the repository root unless stated otherwise.

**Files:**
- `backend/requirements.txt` — pinned deps: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `httpx`, `ruff`, `pytest`, `pytest-anyio`
- `backend/pyproject.toml` — Ruff config (`[tool.ruff]`, `[tool.ruff.lint]`); also defines `[project]` so `pip install -e backend/` works
- `backend/app/__init__.py`, `backend/app/main.py` — minimal FastAPI app, no routes yet
- `backend/ingestion/__init__.py` — empty, makes ingestion a package
- `frontend/package.json` — pinned: `react`, `react-dom`, `typescript`, `vite`, `eslint`, `prettier`, `vitest`, `@testing-library/react`
- `frontend/src/main.tsx`, `frontend/src/App.tsx` — empty shell
- `.eslintrc.cjs` + `.prettierrc`

**Canonical commands (all from repo root):**

| Action | Command |
|---|---|
| Start backend (dev) | `uvicorn backend.app.main:app --reload --app-dir .` |
| Run backend tests | `pytest backend/tests/` |
| Run ingestion | `python -m backend.ingestion.ingest` |
| Run ingestion verify | `python -m backend.ingestion.verify` |
| Backend lint | `ruff check backend/` |
| Start frontend (dev) | `cd frontend && npm run dev` |
| Run frontend tests | `cd frontend && npm run test` |
| Frontend lint | `cd frontend && npm run lint` |

These commands are used verbatim throughout the plan and in the README.

**Prerequisites:** None.

**Acceptance criteria:**
- `uvicorn backend.app.main:app --reload --app-dir .` starts and returns 200 on a GET to `/`
- `cd frontend && npm run dev` starts without error
- `ruff check backend/` passes with zero errors
- `cd frontend && npm run lint` passes with zero errors
- `pytest backend/tests/` runs (zero tests, zero failures)

---

## T1 — Ingestion Script

**Objective:** Populate `backend/data/wind_data.db` with validated, UTC-normalised FUELHH actuals and WINDFOR forecast vintages covering the full analysis window.

**A1 is resolved — `matching.py` is unblocked.**  
The Elexon documentation page was inaccessible during design, but physical-evidence analysis is conclusive: `FUELHH.generation` is **average MW power over the 30-min settlement period**, not MWh energy. If it were MWh, the Jan 2026 values (13,000–16,000) would imply instantaneous power of 26,000–32,000 MW, exceeding total UK installed wind capacity (~25 GW). Both FUELHH and WINDFOR are therefore MW, and the mean of two consecutive half-hour MW values is the correct hourly aggregate. Document this rationale in `decisions.md` at the start of T1 and include it in the `/api/meta` `generationUnitsNote` field and the provenance panel.

**Files:**
- `backend/ingestion/elexon_client.py` — HTTP fetch with exponential backoff
- `backend/ingestion/ingest.py` — orchestrates fetch, validate, store
- `backend/ingestion/verify.py` — post-ingestion coverage report
- `backend/tests/fixtures/windfor_sample.json` — recorded WINDFOR API response
- `backend/tests/fixtures/fuelhh_sample.json` — recorded FUELHH API response
- `backend/tests/test_ingestion.py`

**Ingestion windows:**

| Data | Window | Batch size |
|---|---|---|
| WINDFOR forecasts | `publishDateTimeFrom=2025-12-31T00:00:00Z` to `2026-01-31T23:59:59Z` | Per calendar day |
| FUELHH actuals | `settlementDateFrom=2026-01-01` to `2026-01-31` | Per week |

The WINDFOR window starts Dec 31 because the cutoff for Jan 1 delivery is Dec 31 at 09:20 UTC — without Dec 31 vintages, every Jan 1 hour would be incomplete.

**Ingestion loop (per WINDFOR day):**
1. Fetch with `pageSize=5000`.
2. Assert `len(records) < 5000` — if equal, log an ERROR and split the window into two half-day batches and retry. Never proceed with a potentially truncated response.
3. Log the count and the full list of distinct `publishTime` values for the day.
4. Write inside a single `BEGIN … COMMIT` transaction; roll back on any failure.
5. Assert at least one `publishTime ≤ cutoff(D)` exists for delivery day D; log a WARNING if not.
6. Assert `len(distinct_publish_times_for_day) >= 1`; if exactly 1, log a WARNING (single-vintage day — coverage may be thinner than expected).

**Acceptance criteria:**
- `actuals` has 48 rows per delivery day for all 31 Jan days (1,488 total), or `verify.py` reports the exact shortfall by date
- `forecasts` has at least one eligible vintage (`publishTime ≤ cutoff(D)`) for every delivery hour in Jan 2026
- `meta` records: `ingested_at` (UTC), `delivery_date_from/to`, `forecast_publish_from/to`, per-day `publishTime` audit log (JSON), counts of records dropped and retained
- Re-running produces identical row counts (`INSERT OR REPLACE`; no new rows added)
- `python -m backend.ingestion.verify` exits 0 on success, non-zero with a coverage report on failure
- `verify.py` exits non-zero if **any** day in the WINDFOR window has 0 distinct `publishTime` values

**`verify.py` output (written to stdout/log):**
```
actuals:    1488 rows  (48 per day × 31 days)
forecasts:  NNNN rows  (N vintages × ~NNN records each)
eligible:   744/744 delivery hours have a forecast at cutoff
missing_eligible: [] (list of any uncovered hours)
page_size_warnings: 0
single_vintage_days: [] (days with only 1 distinct publishTime — WARNING)
duplicate_records_dropped: 0
malformed_records_dropped: 0
distinct publishTimes per day: { "2025-12-31": [...], "2026-01-01": [...], ... }
```

**Tests (`test_ingestion.py` — all offline via fixtures):**
- Malformed `generation` (null, string, missing field) → `generation_mw = NULL`, WARNING logged
- Unparseable `startTime` → row dropped, WARNING logged
- Duplicate `(startTime, publishTime)` forecast → single row after insert
- Duplicate `(startTime, settlementPeriod)` actual → single row after insert
- Idempotency: running insert twice → same row count both times
- Truncation detection: fixture where `len(records) == 5000` → ERROR raised, retry triggered
- Zero-record day → ERROR raised, `verify.py` exits non-zero
- **Single-vintage day:** fixture where all records share one `publishTime` → passes insert, logs WARNING, `single_vintage_days` list non-empty in verify output
- **Jan 1 boundary:** fixture with Dec 31 vintages → eligible forecast exists for `2026-01-01T00:00:00Z`
- **Jan 31 boundary:** fixture confirms coverage of `2026-01-31T23:00:00Z`

---

## T2 — Domain Logic + Unit Tests

**Objective:** Pure, independently-tested functions for vintage selection, hourly matching, and metric calculation.

**A1 is resolved — all three modules are unblocked.** `matching.py` uses `actual_mw(H) = mean(generation at H+00:00, generation at H+00:30)` where both values are average MW power. Implement all three modules in order: `selection.py` → `matching.py` → `analytics.py`.

**Files:**
- `backend/app/selection.py`
- `backend/app/matching.py`
- `backend/app/analytics.py`
- `backend/tests/fixtures/golden_metrics.json` — small hand-computed dataset with known MAE/RMSE/bias/nMAE/nRMSE values and completeness
- `backend/tests/test_selection.py`
- `backend/tests/test_matching.py`
- `backend/tests/test_analytics.py`

**Acceptance criteria:**
- `selection.py`: returns `max(publishTime) ≤ cutoff_dt` per hour; hours with no eligible vintage have `missingForecast=True, complete=False`; all comparisons use UTC-aware `datetime` objects
- `matching.py`: aggregates half-hours using `mean(generation at H+00:00, generation at H+00:30)` (both MW); `hoursComplete + hoursIncomplete == hoursTotal` holds for every input; missing actual → `actual_mw = None` (not 0); missing forecast → `forecast_mw = None`; error only computed when both are non-null; genuine `actual_mw = 0.0` (non-null) → hour is complete and included in metrics
- `analytics.py`: metrics match golden fixture within 1e-6; `normalizedOmitted=True` when `mean_actual < 100`; incomplete hours contribute 0 to the numerator by exclusion, not by substituting 0 for missing values

**Tests:**

`test_selection.py`:
- Vintage with `publishTime == cutoff_dt` exactly → eligible
- Vintage with `publishTime == cutoff_dt + 1s` → excluded
- Two vintages both eligible → `max(publishTime)` selected
- No eligible vintage for an hour → `missingForecast=True`
- **Jan 1 delivery, Dec 31 vintage:** `publishTime=2025-12-31T07:30:00Z` ≤ `cutoff(2026-01-01)=2025-12-31T09:20:00Z` → eligible
- **Jan 31 delivery:** `cutoff(2026-01-31)=2026-01-30T09:20:00Z`; vintage at `2026-01-30T07:30:00Z` → eligible
- Post-cutoff vintage at `2026-01-30T09:30:00Z` for Jan 31 delivery → excluded

`test_matching.py`:
- Both half-hours present, non-null → `actual_mw = mean(a, b)`; `complete=True`
- One half-hour null → `actual_mw = None`; `missingActual=True`; `complete=False`
- No forecast selected → `forecast_mw = None`; `missingForecast=True`; `complete=False`
- Both missing → `complete=False`; counted once in `hoursIncomplete`
- Boundary: `2026-01-01T00:00:00Z` (first delivery hour)
- Boundary: `2026-01-31T23:00:00Z` (last delivery hour)
- `hoursComplete + hoursIncomplete == hoursTotal` assertion for varied inputs

`test_analytics.py`:
- Golden fixture: MAE, RMSE, bias match hand-computed values within 1e-6
- nMAE and nRMSE correct against golden
- `mean_actual < 100 MW` → `nmae=None`, `nrmse=None`, `normalizedOmitted=True`
- Completeness = complete / total; correct for mixed complete/incomplete input
- Empty input list → `hoursTotal=0`, `hoursComplete=0`, all metrics `None`, `normalizedOmitted=True`
- Incomplete hours excluded from metric numerators and denominators; their `actual_mw=None` is never replaced with 0
- **Genuine zero:** hour with `actual_mw=0.0` (non-null, both half-hours present) and a valid forecast → `complete=True`; included in metric calculations; not treated as missing

---

## T3 — FastAPI Routes + Pydantic Schemas

**Objective:** Typed, validated HTTP endpoints exposing the domain logic.

**Prerequisites:** T2 fully complete (including `matching.py` after A1 lifted).

**Files:**
- `backend/app/schemas.py`
- `backend/app/repository.py` — raw SQL returning dataclasses; no business logic
- `backend/app/routes/health.py`
- `backend/app/routes/meta.py`
- `backend/app/routes/metrics.py`
- `backend/app/routes/timeseries.py`
- `backend/app/main.py` — register routers, configure CORS
- `backend/tests/test_routes.py`

**Database failure policy (applied consistently):**  
On startup, FastAPI reads `WIND_DB_PATH` (env var, default `backend/data/wind_data.db`). If the file is absent or `meta` has no rows:
- `/health` returns `200 { "status": "degraded", "dataLoaded": false }` — always 200 so Render's health check does not restart the container in a crash loop
- All other routes return `503 { "error": "data_unavailable", "message": "Database not loaded." }`

This policy is consistent across startup and runtime.

**Acceptance criteria:**
- `/health`: 200 always; `dataLoaded: true` when DB present and populated
- `/api/meta`: ingestion metadata including `deliveryDateRange`, `forecastPublishRange`, and `generationUnitsNote` — a string stating that `FUELHH.generation` is treated as average MW power, the physical-evidence basis, and that official documentation was inaccessible
- `/api/metrics?from=&to=`: aggregate metrics; `hoursComplete + hoursIncomplete == hoursTotal`; `nmae`/`nrmse` are JSON `null` (not 0) when `normalizedOmitted`
- `/api/timeseries?from=&to=`: per-hour points; `forecast`, `actual`, `error`, `selectedPublishTime` are JSON `null` for incomplete hours (never 0)
- Both `/api/metrics` and `/api/timeseries` use the same `cutoff_dt` from the same derivation function — given the same window they agree
- `from > to` → 400; date outside 2026-01-01 to 2026-01-31 → 400; consistent error envelope `{ "error": "code", "message": "..." }`

**Tests (`test_routes.py`):**
- All four endpoints happy path with DB fixture
- `/api/metrics` and `/api/timeseries` on the same window → same `hoursComplete`, `hoursIncomplete`, `hoursTotal`
- `from > to` → 400
- Date outside Jan 2026 → 400
- DB absent → `/health` 200 `dataLoaded:false`; `/api/metrics` 503
- `hoursComplete + hoursIncomplete == hoursTotal` asserted in every metrics response
- `null` (not 0) in `nmae`/`nrmse` when `normalizedOmitted: true`
- Incomplete timeseries point: `forecast`, `actual`, `error`, `selectedPublishTime` all `null`

---

## T4 — Frontend Scaffold + Typed API Client

**Objective:** TypeScript types mirroring backend schemas; fetch wrapper with request-state hooks; stale-request cancellation on filter change.

**Prerequisites:** T0 (scaffold). T3 must be running for the live integration smoke only — the client and hooks can be built and tested against mocked responses first.

**Note on fixture labelling:** Any test or Storybook fixture used before real backend data is available must be marked `// TEST FIXTURE — not real data` at the top of the file.

**Files:**
- `frontend/src/api/types.ts` — TypeScript interfaces matching backend Pydantic schemas
- `frontend/src/api/client.ts` — typed fetch wrapper; `{ data, loading, error }`
- `frontend/src/hooks/useMetrics.ts`
- `frontend/src/hooks/useTimeseries.ts`
- `frontend/tests/client.test.ts`

**Stale-request handling:**  
`useMetrics` and `useTimeseries` use an `AbortController` keyed to the current request. When the date filter changes, the in-flight request is cancelled before a new one starts. This prevents an earlier slow response overwriting a newer one.

```typescript
// Pattern (not final code):
useEffect(() => {
  const controller = new AbortController();
  fetch(url, { signal: controller.signal }).then(...);
  return () => controller.abort();
}, [from, to]);
```

**Acceptance criteria:**
- TypeScript compiles with zero errors
- `useMetrics` and `useTimeseries` expose `{ data, loading, error }`
- Stale-request: changing `from`/`to` cancels the in-flight request
- `null` fields on incomplete timeseries points typed as `number | null`, not `number | undefined`
- Client fetches `/api/meta` and `/api/metrics` against live backend (smoke only)

**Tests (`client.test.ts`):**
- Mocked successful fetch → correct `data`, `loading: false`, `error: null`
- Mocked error response → `error` populated, `data: null`
- Filter change mid-request → previous request aborted, new request fired
- `null` in `forecast`/`actual`/`error` fields typed and handled without coercion to 0

---

## T5 — Dashboard UI

**Objective:** Full interactive dashboard rendering from live backend data.

**Prerequisites:** T4. Components may be built with labelled fixtures before T3 is complete; switch to live hooks once backend is up.

**Files:**
- `frontend/src/components/FilterBar.tsx`
- `frontend/src/components/ForecastChart.tsx`
- `frontend/src/components/MetricCards.tsx`
- `frontend/src/components/IntervalTable.tsx`
- `frontend/src/components/ProvenancePanel.tsx`
- `frontend/src/App.tsx` — layout, persistent disclaimer
- `frontend/tests/` — component tests

**Consistency requirement:** chart data points, table rows, and metric cards all derive from the same API call results. The chart must not show a data point where the table shows a gap (or vice versa). Incomplete hours render as a visible gap in the chart and a greyed-out row in the table — never as zero.

**Acceptance criteria:**
- Date filter constrained to Jan 2026; changing it cancels any in-flight request and fires a new one
- Chart: dual-series forecast vs actual; hover tooltip shows forecast MW, actual MW, error MW; gap (not zero) at incomplete hours
- Metric cards: MAE, RMSE, bias (MW), nMAE/nRMSE (% or "N/A"); completeness %
- Interval table: per-hour rows sortable by absolute error; incomplete rows marked, not zero-filled
- Provenance panel: cutoff definition with "(provisional)" label; `selectedPublishTime` range for queried window; units (MW); timezone note; ingestion timestamp; delivery date range; forecast publish range; data-quality note (count of incomplete hours and reason); generation-units assumption: *"FUELHH generation treated as average MW power — confirmed by physical plausibility; official documentation was inaccessible"*
- Procurement-scope disclaimer visible at all times (not dismissible)
- Loading, empty, and error states for all components; no silent failures; no fabricated values

**Tests:**
- Chart renders two series from mocked timeseries; gap at incomplete point (not zero)
- Cards display mocked metrics; `normalizedOmitted: true` → "N/A" rendered (not 0)
- Filter change aborts in-flight request; new request fired with updated params
- Error state renders on backend 500; previous data cleared
- Empty state renders when `points: []` returned

---

## T6 — Docker + docker-compose

**Objective:** Full app runnable locally with a single `docker compose up`.

**Prerequisites:** T3 (backend complete), T5 (frontend complete).

**Files:**
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.env.example`

**`VITE_BACKEND_URL` is a build-time variable** — it is baked into the Vite output at `npm run build` time, not injected at runtime. The frontend Dockerfile must pass it as a build arg:

```dockerfile
# frontend/Dockerfile
ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
RUN npm run build
```

In `docker-compose.yml`:
```yaml
frontend:
  build:
    args:
      VITE_BACKEND_URL: http://localhost:8000
```

In production (Render), `VITE_BACKEND_URL` is set as an environment variable on the static site's build configuration — it resolves to the Render web service URL before the build runs.

**Database packaging:**  
The `backend/Dockerfile` must `COPY data/wind_data.db /app/data/wind_data.db`. If the file is absent from the build context, the Docker build fails explicitly. On container startup, FastAPI checks `WIND_DB_PATH` exists and `meta` has at least one row; if not, `/health` returns `dataLoaded: false` and all data routes return 503.

**CORS:**  
`FRONTEND_ORIGIN` is required in production. In `docker-compose.yml` it defaults to `http://localhost:5173`. The backend FastAPI app reads this env var to set `allow_origins`. Never use `allow_origins=["*"]` except as an explicit dev-only override.

**Acceptance criteria:**
- `docker compose up` builds and starts both services without error
- `wind_data.db` absent from build context → `docker build` fails with a clear error
- `curl http://localhost:8000/health` → `200 { "status": "ok", "dataLoaded": true }`
- Dashboard loads at `http://localhost:5173` and renders live data
- CORS: frontend origin allowed; a request from a different origin is rejected

**Tests:** Manual smoke test on compose stack.

---

## T7 — Deploy to Render

**Objective:** Public HTTPS URL serving the full application.

**Prerequisites:** T6 passing locally.

**Steps:**
1. Push repo to GitHub (anonymous name `wind-accuracy-dashboard`); confirm `backend/data/wind_data.db` is committed (or added as a Git LFS file if >100 MB)
2. Create **Render Web Service** from `backend/Dockerfile`
   - Set env var `FRONTEND_ORIGIN` to the Render static site URL (known after step 3; update after initial deploy)
   - Set `DECISION_CUTOFF_TIME=09:20`, `WIND_DB_PATH=/app/data/wind_data.db`
   - Health check path: `/health`
3. Create **Render Static Site** from `frontend/`
   - Set build command: `npm run build`
   - Set env var `VITE_BACKEND_URL` to the Render web service URL
   - Set publish directory: `dist`
4. After both are deployed, confirm `FRONTEND_ORIGIN` on the backend matches the actual static site URL
5. Record the deployment URL in `decisions.md` and README

**Deployment debugging checklist (allocate time for this):**
- CORS error in browser console → check `FRONTEND_ORIGIN` matches the exact static site origin (scheme + host + no trailing slash)
- `/health` returns `dataLoaded: false` → `wind_data.db` not copied into image; verify `COPY` instruction and that the file is in the build context
- Render free-tier cold start (~15 min sleep): note in demo, consider deploying on a paid instance tier for the demo if reliability matters
- 404 on frontend routes → ensure Render static site is configured to rewrite all paths to `index.html`

**Acceptance criteria:**
- `/health` returns `200 { "status": "ok", "dataLoaded": true }` over HTTPS
- Dashboard loads at the public URL and renders Jan 2026 data
- CORS: no errors in browser console when frontend fetches backend

---

## T8 — README + AI Usage Disclosure

**Objective:** Complete, accurate README at the repo root.

**Prerequisites:** T7.

**Contents (required sections):**
- Project overview and procurement-scope disclaimer (first thing after the title)
- Repository structure
- Local setup — Docker path: `docker compose up`
- Local setup — Non-Docker path: `pip install -r backend/requirements.txt`, then `uvicorn backend.app.main:app --reload --app-dir .`; separately `cd frontend && npm install && npm run dev`
- Ingestion: `python -m backend.ingestion.ingest` then `python -m backend.ingestion.verify`
- Tests: `pytest backend/tests/` and `cd frontend && npm run test`
- Environment variables table (all vars, defaults, required/optional)
- Timezone assumption: UTC == UK local for Jan 2026 (no DST); `DECISION_CUTOFF_TIME` is provisional
- FUELHH unit assumption (A1): state that `generation` is treated as average MW power; explain the physical-evidence basis (MWh interpretation exceeds UK installed capacity); note that official documentation was inaccessible; state the aggregation formula `actual_mw(H) = mean(H+00:00, H+00:30)`
- Data-quality notes: completeness definition, missing-record handling, no zero-imputation
- Deployment URL
- AI tool usage disclosure

---

## T9 — Demo Preparation

**Objective:** Two-part unlisted YouTube video (≤ 10 min total).

**Prerequisites:** T7, T8.

**Part 1 — Customer pitch (≤ 5 min):**
Frame the business problem → select a Jan 2026 delivery date → read chart and accuracy cards → highlight bias and completeness → state the decision-time cutoff and provisional nature → explain procurement-scope limitation → close with value.

**Part 2 — Technical walkthrough (≤ 5 min):**
Architecture diagram → ingestion and SQLite bundling → cutoff selection and leak prevention → hourly matching and unit semantics (A1 outcome) → metric formulas → API contracts → tests and fixtures → Docker + Render deployment → env/CORS/health.

---

## Schedule (~17h)

Rebalanced to give more time to deployment debugging and contingency.

| Task | Est. | Notes |
|---|---|---|
| T0 Scaffold | 0.5h | |
| T1 Ingestion | 2.5h | A1 resolution at start; adds ~0.5h if docs are hard to find |
| T2 Domain logic + tests | 3h | All three modules unblocked (A1 resolved); implement in order: selection → matching → analytics |
| T3 API routes | 2h | |
| T4 FE scaffold/client | 1.5h | Can overlap with T2/T3 using labelled fixtures |
| T5 Dashboard UI | 3h | |
| T6 Docker | 1h | |
| T7 Deploy + debug | 2h | Extra hour vs prior plan for CORS/DB/cold-start debugging |
| T8 README | 0.5h | |
| T9 Demo prep | 0.5h | |
| Contingency | 0.5h | |
| **Total** | **17h** | |

Priority order: data correctness → domain tests → API → frontend → deployment → demo.

**Parallelism opportunity:** T4 (client scaffold + hooks) can start as soon as T0 is done, using labelled static fixtures. Connect to live backend once T3 is complete.
