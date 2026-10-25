# Task Checklist

Track implementation progress. Mark each item `[x]` when done. Keep decisions.md updated as real choices are made during each task.

---

## T0 — Scaffold Monorepo
- [ ] Create `backend/` and `frontend/` directory structure
- [ ] `backend/requirements.txt` with pinned deps (fastapi, uvicorn[standard], pydantic>=2, httpx, ruff, pytest)
- [ ] `backend/app/main.py` — minimal FastAPI app, no routes
- [ ] `frontend/package.json` with pinned deps (react, react-dom, typescript, vite, eslint, prettier, vitest)
- [ ] `frontend/src/main.tsx` + `frontend/src/App.tsx` — empty shell
- [ ] Ruff config (`.ruff.toml` or `pyproject.toml`)
- [ ] ESLint + Prettier config
- [ ] `ruff check backend/` passes
- [ ] `cd frontend && npm run lint` passes
- [ ] Both apps start locally without errors

---

## T1 — Ingestion Script
- [ ] Resolve Assumption A1: confirm FUELHH `generation` units from authoritative Elexon docs — **record result in decisions.md**
- [ ] `backend/ingestion/elexon_client.py` — HTTP fetch with exponential backoff (429 handling)
- [ ] WINDFOR fetch: per-day `publishDateTimeFrom/To` windows, `pageSize=5000`, truncation detection
- [ ] FUELHH fetch: per-week `settlementDateFrom/To` windows, `fuelType=WIND`
- [ ] Pydantic models for WINDFOR and FUELHH records
- [ ] UTC normalisation for all timestamps
- [ ] SQLite schema: `actuals`, `forecasts`, `meta` tables
- [ ] `INSERT OR REPLACE` for idempotency; transactions per batch
- [ ] Per-day logging of distinct `publishTime` values
- [ ] `meta` row records `ingested_at`, delivery range, forecast publish range
- [ ] `backend/ingestion/verify.py` — coverage checks, exits non-zero on failure
- [ ] Record offline test fixtures for WINDFOR and FUELHH sample responses
- [ ] `backend/tests/test_ingestion.py` (all offline):
  - [ ] Malformed `generation` → NULL + warning
  - [ ] Unparseable timestamp → row dropped + warning
  - [ ] Duplicate forecast row → single row retained
  - [ ] Duplicate actual row → single row retained
  - [ ] Idempotency (two runs = same counts)
  - [ ] Truncation detection: `len == pageSize` raises error
  - [ ] Zero-record day raises error
- [ ] `python -m ingestion.ingest` populates DB successfully
- [ ] `python -m ingestion.verify` passes

---

## T2 — Domain Logic + Unit Tests
- [ ] `backend/app/selection.py` — cutoff vintage selection, UTC-aware comparisons only
- [ ] `backend/tests/test_selection.py`:
  - [ ] Vintage at exactly cutoff → eligible
  - [ ] Vintage 1 s after cutoff → excluded
  - [ ] Multiple vintages → `max(publishTime)` selected
  - [ ] No eligible vintage → `complete=False`
- [ ] `backend/app/matching.py` — **implement after A1 confirmed**
  - [ ] Aggregates two FUELHH half-hours per delivery hour
  - [ ] Sets `complete`, `missingForecast`, `missingActual` flags
  - [ ] `hoursComplete + hoursIncomplete == hoursTotal` invariant
- [ ] `backend/tests/test_matching.py`:
  - [ ] Both half-hours present → mean aggregation
  - [ ] One half-hour null → `missingActual=True, complete=False`
  - [ ] No forecast → `missingForecast=True, complete=False`
  - [ ] Hour with both missing → counted once in `hoursIncomplete`
  - [ ] Boundary hours 00:00 and 23:00
- [ ] `backend/tests/fixtures/golden_metrics.json` — hand-computed expected outputs
- [ ] `backend/app/analytics.py` — MAE, RMSE, bias, nMAE, nRMSE, completeness
- [ ] `backend/tests/test_analytics.py`:
  - [ ] Golden fixture round-trip (within 1e-6)
  - [ ] nMAE/nRMSE correct
  - [ ] `mean_actual < 100 MW` → `normalizedOmitted=True`
  - [ ] Completeness ratio
  - [ ] Empty input → zero hours

---

## T3 — FastAPI Routes + Pydantic Schemas
- [ ] `backend/app/schemas.py` — request + response Pydantic models
- [ ] `backend/app/repository.py` — raw SQL, returns dataclasses, no business logic
- [ ] `backend/app/routes/health.py` — `/health`
- [ ] `backend/app/routes/meta.py` — `/api/meta`
- [ ] `backend/app/routes/metrics.py` — `/api/metrics`
- [ ] `backend/app/routes/timeseries.py` — `/api/timeseries`
- [ ] `backend/app/main.py` — register routers, CORS config
- [ ] `metrics` and `timeseries` share the same `cutoff_dt` derivation function
- [ ] `backend/tests/test_routes.py`:
  - [ ] Happy path all four endpoints
  - [ ] `from > to` → 400 with error envelope
  - [ ] Date outside Jan 2026 → 400
  - [ ] Metrics and timeseries use identical cutoff for same window
  - [ ] `hoursComplete + hoursIncomplete == hoursTotal`
  - [ ] Missing DB → `/health` returns `dataLoaded: false`

---

## T4 — Frontend Scaffold + Typed API Client
- [ ] `frontend/src/api/types.ts` — TypeScript interfaces matching backend schemas
- [ ] `frontend/src/api/client.ts` — typed fetch wrapper, `{ data, loading, error }`
- [ ] `frontend/src/hooks/useMetrics.ts`
- [ ] `frontend/src/hooks/useTimeseries.ts`
- [ ] TypeScript compiles with zero errors
- [ ] `frontend/tests/client.test.ts`:
  - [ ] Mocked fetch returns valid response → correct `data` state
  - [ ] Mocked fetch returns error → correct `error` state
  - [ ] Loading state transitions

---

## T5 — Dashboard UI
- [ ] `frontend/src/components/FilterBar.tsx` — date/range picker, constrained to Jan 2026
- [ ] `frontend/src/components/ForecastChart.tsx` — dual-series line chart, hover tooltip
- [ ] `frontend/src/components/MetricCards.tsx` — MAE, RMSE, bias, nMAE/nRMSE ("N/A" when omitted), completeness %
- [ ] `frontend/src/components/IntervalTable.tsx` — per-hour rows, sortable by absolute error
- [ ] `frontend/src/components/ProvenancePanel.tsx` — cutoff ("provisional"), `selectedPublishTime` range, units, timezone note, ingestion timestamp, delivery/forecast ranges, completeness, data-quality note
- [ ] `frontend/src/App.tsx` — layout, persistent procurement-scope disclaimer
- [ ] Loading, empty, error states for all components
- [ ] Accessibility: keyboard-navigable controls, labelled inputs
- [ ] Frontend tests:
  - [ ] Chart renders dual series from mocked timeseries
  - [ ] Cards show mocked metrics; `normalizedOmitted` → "N/A"
  - [ ] Filter change triggers new fetch with updated params
  - [ ] Error state renders on backend 500
  - [ ] Empty state renders on no-data selection

---

## T6 — Docker + docker-compose
- [x] `backend/Dockerfile` — python:3.12-slim, copies `data/wind_data.db`, runs uvicorn
- [x] `frontend/Dockerfile` — node build stage, nginx serve
- [x] `docker-compose.yml` — backend + frontend, env vars wired
- [x] `.env.example` documenting all vars
- [x] Backend startup asserts `wind_data.db` exists and `meta` has a row
- [x] `docker compose up` starts both services
- [x] `curl http://localhost:8000/health` → `200 { "status": "ok", "dataLoaded": true }`
- [x] Dashboard loads at `http://localhost:5173`

---

## T7 — Deploy to Render
- [x] Prepare `render.yaml` blueprint with backend Docker service and frontend static site
- [x] Configure health check path (`/health`), build arguments (`VITE_BACKEND_URL`), and SPA rewrites (`/* -> /index.html`)
- [x] Document deployment steps, CORS origin binding, and cold-start expectations in README and `render.yaml`
- [ ] Push repo to GitHub (`wind-accuracy-dashboard`) and connect Blueprint in Render dashboard
- [ ] Verify live HTTPS endpoints and record live URLs in README and `decisions.md`

---

## T8 — README + AI Usage Disclosure
- [x] Project structure section
- [x] Local setup: Docker path and non-Docker path
- [x] Ingestion commands and verify commands
- [x] Test commands (pytest, npm run test)
- [x] Environment variables table
- [x] Timezone and cutoff assumption (UTC == UK local for Jan 2026; 09:20 UTC provisional)
- [x] FUELHH unit assumption status (A1) and resolution
- [x] Data-quality notes (completeness, missing records)
- [x] Procurement-scope disclaimer
- [x] AI tool usage disclosure
- [x] Deployment instructions & configuration guide

---

## T9 — Demo Preparation
- [x] Customer pitch script (≤ 5 min): problem → date selection → chart → metrics → bias → cutoff/provisional → disclaimer → value (`docs/DEMO_PART1_CUSTOMER_PITCH.md`)
- [x] Technical walkthrough script (≤ 5 min): architecture → ingestion → cutoff selection → matching → metrics → API → tests → Docker/Render (`docs/DEMO_PART2_TECHNICAL_WALKTHROUGH.md`)
- [ ] Record unlisted YouTube video (≤ 10 min total, two parts)
- [ ] Verify submission form links work

---

## Ongoing: decisions.md
Update after each real decision during implementation:
- [x] A1: FUELHH unit confirmed → document formula used
- [x] A2: Jan 2026 vintage availability confirmed during ingestion
- [x] A3: Publication schedule for all Jan days logged and reviewed
- [x] A4: pageSize adequacy confirmed or adjusted
- [x] Any deviation from ARCHITECTURE.md or IMPLEMENTATION_PLAN.md

