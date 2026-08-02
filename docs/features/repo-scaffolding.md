# Repository scaffolding & monorepo layout

## Overview

Establishes the empty but correctly structured `backend/` and `frontend/` trees so every later story
has a fixed place to land code, per plan §8 ("Suggested Repository / Folder Structure"). This is
structural scaffolding only — no business logic, no working endpoints beyond a trivial liveness probe.
The backend is a FastAPI app with the domain/infrastructure separation the plan's Dependency Inversion
rule depends on (`app/domain/**` interfaces vs. `app/infrastructure/**` implementations); the frontend is
a Next.js 15 App Router app with the three route groups (`(marketing)`, `(auth)`, `(portal)`) the plan's
§9 frontend architecture is built around.

## Interfaces / contracts

None — STORY-001 is scaffold-only per `implementation_task.md` ("Interfaces/contracts touched: none
yet"). The packages below exist as empty containers for interfaces/implementations introduced by later
stories:

- `backend/app/core/` — config loader, security, DI container (STORY-003+)
- `backend/app/api/` — routers per domain (STORY-006, STORY-010, STORY-023, ...)
- `backend/app/domain/{ingestion,processing,retrieval,generation,safety,chat,billing,users}/` —
  domain interfaces and business logic, one package per bounded context
- `backend/app/infrastructure/{db/postgres,db/mongo,storage,vectorstore}/` — concrete provider
  implementations (STORY-004, STORY-005, STORY-017, STORY-045, STORY-046, STORY-047)
- `backend/app/workers/` — Celery tasks (STORY-014+)
- `frontend/app/(marketing)/`, `frontend/app/(auth)/`, `frontend/app/(portal)/` — Next.js App Router
  route groups (STORY-007, STORY-024, STORY-025, STORY-034, STORY-051, STORY-058)
- `frontend/{components,features,lib,styles,tests}/` — shared UI, feature-sliced modules, API client
  utilities, Tailwind styles, and the frontend test suite

## Config knobs

None yet. `ConfigService` and the env var / `system_config` precedence chain are introduced in
STORY-003; this story deliberately ships without a `.env.example` since no bootstrap variable is read
yet (`backend/app/main.py`'s health route and the frontend placeholder pages need no configuration). See
[docs/reference/configuration.md](../reference/configuration.md) for the precedence rule that will apply
once config keys exist.

## Testing

- Backend: `backend/tests/e2e/test_health.py` — proves the acceptance criterion that
  `uvicorn app.main:app` serves a 200 on `/health`, via an in-process `httpx.AsyncClient` against the
  same ASGI `app` instance. Run with:
  ```
  cd backend
  python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
  python -m pytest tests/
  ```
  (also manually verified by running `uvicorn app.main:app` directly and curling `/health` → 200)
- Frontend: `frontend/tests/route-groups.test.tsx` — Vitest + React Testing Library, renders each of the
  three route-group placeholder pages (`(marketing)`, `(auth)/login`, `(portal)/dashboard`) and asserts
  their content. Run with:
  ```
  cd frontend
  npm install
  npm run test
  ```
  (also manually verified by running `npm run dev` and curling `/`, `/login`, `/dashboard` → 200 each)
- `backend/tests/{unit,integration}/` and the rest of `frontend/tests/` remain empty at this stage;
  STORY-002 wires the CI jobs that allow zero-test suites to pass, and later stories populate these
  directories as their own acceptance criteria require.

## Story references

- STORY-001 — Repository scaffolding & monorepo layout
