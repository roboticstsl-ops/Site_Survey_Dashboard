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
backend/    FastAPI service. Phase 0/1 scaffold so far: health endpoints,
            Pydantic domain models (BUILD_SPEC section 4), the feasibility
            rule (identical to the phone app's), and a tested
            svs_draft_v3 -> canonical-survey mapper. No live routes yet —
            those need real Atlas credentials (Phase 2).
frontend/   the dashboard web app. Not started — first decision to make is
            framework choice (see BUILD_SPEC section 9 for the UI spec).
docs/       BUILD_SPEC.pdf (source of truth) + anything else written about
            the API/data-migration/operations as those get built.
infra/      laptop/ = how to run the MVP test deployment. cloud/ = later.
.github/workflows/android.yml   builds mobile/ into an APK, same as before,
            just re-pointed at its new path in this repo.
```

## Where things actually stand (Phase 0 / start of Phase 1)

- [x] Existing working app imported into `mobile/` — nothing about it changed.
- [x] Domain models for the full canonical survey (`backend/app/domain/models.py`).
- [x] Feasibility rule ported 1:1 from the phone app, unit-tested.
- [x] `svs_draft_v3` → canonical-survey mapper, unit-tested against a fixture
      draft — unknown/dropped fields land in `legacy.unmapped`, never silently lost.
- [x] Storage adapter interface + `LocalFileStorage` (BUILD_SPEC section 3.2 rule 3).
- [x] Health/readiness endpoints, settings, Mongo index definitions.
- [ ] Everything requiring a live Mongo Atlas connection: auth, CRUD, sync,
      the actual `import-legacy-draft` endpoint, dashboard API. That's Phase 2 —
      needs an Atlas connection string and a decision on where secrets live
      for the laptop deployment.
- [ ] `frontend/` dashboard — not started. Framework choice is open.
- [ ] Wiring `mobile/` to talk to this backend at all (it's fully offline
      today; BUILD_SPEC wants "submit when online", not live sync).

## Running the backend locally

See [`infra/laptop/README.md`](infra/laptop/README.md).

```
cd backend
pip install -e ".[dev]"
pytest      # runs the domain-model tests without needing Mongo
```

## Related

- The Android app also ships from its own repo history at
  [Elevator-assesment-app](https://github.com/roboticstsl-ops/Elevator-assesment-app) —
  `mobile/` here is a copy of that, going forward this repo is where the
  survey app + dashboard evolve together per `BUILD_SPEC.pdf`.
