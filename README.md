# Elevator RF Survey — dashboard + backend

Android-first field-survey app + a searchable web dashboard for elevator
RF/LTE feasibility visits. This repo is the monorepo defined by
[`docs/BUILD_SPEC.pdf`](docs/BUILD_SPEC.pdf) — that document is the single
source of truth for scope, data model, API contract and phased plan. Read it
before changing architecture; this README is just the map + how to run things.

> **Note on an earlier draft of this README:** the very first commit here
> planned a Supabase/Postgres backend. `BUILD_SPEC.pdf` supersedes that —
> the backend is **FastAPI + MongoDB Atlas Free** (laptop-hosted for the
> first test release), per the client's own build spec. Documented rather
> than silently dropped, per that spec's own guardrail #2.

## Layout

```
mobile/     the existing, working Capacitor app — moved here as-is.
            www/index.html (the whole app), template.docx, the four native
            Android plugins, tools/make_template.py, its own GitHub Actions
            APK build. Untouched until an equivalent backend-integrated
            flow is proven (BUILD_SPEC guardrail #1).
backend/    FastAPI service. Domain models (BUILD_SPEC section 4), the
            feasibility rule (identical to the phone app's), a tested
            svs_draft_v3 -> canonical-survey mapper, and — Phase 2 — the read
            API the dashboard talks to: dashboard summary, survey list
            (search/filter/sort/paginate) + detail, reports + an
            authenticated DOCX download, one login endpoint, and file
            serving for photos. Needs a real MONGODB_URI to do anything past
            /healthz; run `tools/seed_admin.py` once against a fresh database
            so there's a user to sign in with.
frontend/   the dashboard web app: a single static HTML/JS file (no build
            step, matching this project's own convention) wired to the
            backend above via a JSDoc-typed fetch client. Handles loading,
            empty, offline, and API-error states. Framework choice is still
            open if this ever needs one — plain JS has been enough so far.
docs/       BUILD_SPEC.pdf (source of truth) + anything else written about
            the API/data-migration/operations as those get built.
infra/      laptop/ = how to run the MVP test deployment. cloud/ = later.
.github/workflows/android.yml   builds mobile/ into an APK, same as before,
            just re-pointed at its new path in this repo.
```

## Where things actually stand (Phase 2)

- [x] Existing working app imported into `mobile/` — nothing about it changed.
- [x] Domain models for the full canonical survey (`backend/app/domain/models.py`),
      including structured `integration.connector` (type/positions/pitch/gender)
      alongside the original free-text `connectors` field — never inferred from it.
- [x] Feasibility rule ported 1:1 from the phone app, unit-tested.
- [x] `svs_draft_v3` → canonical-survey mapper, unit-tested against a fixture
      draft — unknown/dropped fields land in `legacy.unmapped`, never silently lost.
- [x] Storage adapter interface + `LocalFileStorage` (BUILD_SPEC section 3.2 rule 3).
- [x] Health/readiness endpoints, settings, Mongo index definitions.
- [x] Dashboard read API: `/dashboard/summary`, `/surveys` (search/filter/sort/
      paginate + a `/surveys/facets` endpoint for filter-dropdown values),
      `/surveys/{id}`, `/surveys/{id}/reports` + authenticated `.../download`,
      `/files/by-key/{storage_key}`, `/auth/login`. Verified end-to-end against
      a real local MongoDB + a real Python 3.11 FastAPI process (this dev
      machine only has Python 3.9) — no fake backend data shipped; the DB is
      genuinely empty until real surveys land in it.
- [x] `frontend/` dashboard now calls that API for everything — no mock
      survey data left in the page. Loading/empty/offline/API-error states,
      a minimal login modal for the one protected route (report download),
      Connector Type column + filter, and a Pinout & Integration tab.
- [ ] Write/sync endpoints (create/update survey from the mobile app,
      `import-legacy-draft`) — Phase 3.
- [ ] Wiring `mobile/` to talk to this backend at all (it's fully offline
      today; BUILD_SPEC wants "submit when online", not live sync).
- [ ] Railing diagram rendering from `railings.<side>.drawing` stroke data —
      the dashboard currently shows the numeric `dimensions_mm` table only.

## Running the backend locally

See [`infra/laptop/README.md`](infra/laptop/README.md).

```
cd backend
pip install -e ".[dev]"
pytest                              # domain-model + connector-validation tests, no Mongo needed
cp ../.env.example ../.env          # fill in MONGODB_URI (MONGODB_TLS=false for a local/docker Mongo)
python tools/seed_admin.py --email you@example.com --password ...   # once, so login works
uvicorn app.main:app --reload
```

## Running the frontend locally

`frontend/index.html` is a static file — open it directly, or serve it:

```
cd frontend
python3 -m http.server 8080
```

It calls the backend at `http://localhost:8000` by default; point it elsewhere by
setting `window.API_BASE` before the page's own script runs, or add
`http://localhost:8080` to the backend's `CORS_ALLOWED_ORIGINS` either way.

## Related

- The Android app also ships from its own repo history at
  [Elevator-assesment-app](https://github.com/roboticstsl-ops/Elevator-assesment-app) —
  `mobile/` here is a copy of that, going forward this repo is where the
  survey app + dashboard evolve together per `BUILD_SPEC.pdf`.
