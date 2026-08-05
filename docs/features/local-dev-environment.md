# Local dev environment (docker-compose)

## Overview

Provides the one-command local infrastructure stack — Postgres, MongoDB, Redis, and Qdrant — that every
Phase 1+ story (document persistence, `system_config`, Celery/rate-limiting, vector storage) connects
against during local development, per plan §8/Phase 0 ("one-command local environment for all infra
dependencies"). `docker-compose.yml` declares only these four infra services; it deliberately ships no
application service (backend/frontend/worker) — Celery/worker wiring is STORY-014's scope, not this
one's.

## Interfaces / contracts

None — this is an infra-only story (`implementation_task.md` lists no interfaces/contracts touched for
STORY-008). The deliverables are `docker-compose.yml` itself, `.env.example`, and
`docs/runbooks/local-dev-setup.md`.

## Config knobs

`.env.example` documents every bootstrap-level variable `Settings`
(`backend/app/core/settings.py`) reads at process start, and each one is kept consistent with
`docker-compose.yml`'s own service defaults so a straight `cp .env.example .env` connects with zero
edits:

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` — Postgres
  connection (SQLAlchemy async/asyncpg). Fixed a real mismatch in this pass: `.env.example` previously
  documented `POSTGRES_PASSWORD` as blank while `docker-compose.yml`'s `postgres` service defaults to
  `${POSTGRES_PASSWORD:-raas}` — a human copying the template verbatim would get an empty-password
  client against a `raas`-password server. Both now say `raas` (explicitly local-dev-only, see the
  comment in `.env.example`).
- `MONGO_URI`, `MONGO_DB` — Mongo connection (Motor), also where `system_config` itself lives.
- `REDIS_URL` — Redis connection (Celery broker/result backend, rate limiting, token blacklist).
- `QDRANT_URL`, `QDRANT_API_KEY` — Qdrant connection (default vector store).

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule
(`system_config` → env vars → `.env` defaults) these variables sit at layers 2/3 of.

A separate, non-`.env.example` fix landed alongside this story: `backend/requirements.txt` now pins
`pymongo==4.8.0`. `motor==3.5.1` calls a `pymongo.cursor` private API (`_QUERY_OPTIONS`) that
`pymongo>=4.9` removed, which made `AsyncIOMotorClient` (used by `ConfigService`'s Mongo-backed
`system_config` resolution in `backend/app/core/config.py`) fail with an `ImportError` the moment a
newer `pymongo` was present — surfaced while verifying this story's second acceptance criterion.

## Testing

There is no permanent automated test for `docker-compose.yml` itself — bringing up compose infra isn't
something `pytest` drives, and `backend/tests/integration/` intentionally uses ephemeral
`testcontainers` instances per `.claude/rules/testing-standards.md` rather than this shared compose
stack (a testcontainers-based CI sweep against the real interfaces is STORY-060's scope). This story's
acceptance criteria were instead verified directly:

- **`docker compose up -d` brings up all four services healthy**: from a clean `docker compose down -v`,
  `docker compose up -d` then `docker compose ps` showed `postgres`, `mongo`, `redis`, and `qdrant` all
  reach `healthy` within ~20 seconds.
- **Backend connects successfully against these containers**: ran a one-off script exercising the
  backend's own connection code — `app.infrastructure.db.postgres.session.create_postgres_engine`
  (`SELECT 1` via SQLAlchemy async/asyncpg), `motor.motor_asyncio.AsyncIOMotorClient(...).admin.command
  ("ping")`, `redis.asyncio.from_url(...).ping()`, and an HTTP `GET` against Qdrant's REST root — all
  resolved through `app.core.settings.get_settings()` using exactly `.env.example`'s documented
  local-dev values (set as process env vars, no real `.env` read or written). All four services
  responded successfully.
  - One environment-specific wrinkle surfaced and was ruled out as a code issue: this machine has a
    native PostgreSQL service already bound to host port `5432`, which intercepts connections meant for
    the container. Confirmed by remapping the compose stack to `POSTGRES_PORT=15432` for the check,
    at which point the exact same `.env.example` credentials connected cleanly — proving
    `docker-compose.yml`/`.env.example` are correct and the conflict is host-local. Documented as a
    troubleshooting entry in the runbook rather than "fixed" in compose (the default `5432` mapping is
    intentional and matches `.env.example`).
  - Reran the full existing backend suite after the `pymongo` pin (138 unit + 38 integration tests,
    the latter via `testcontainers`, unaffected by the host port-5432 conflict since `testcontainers`
    binds a random host port) — all green, confirming zero regression.
- Run the regression suite yourself: `cd backend && python -m pytest tests/unit tests/integration -q`.

## Story references

- STORY-008 — Local dev environment (docker-compose: Postgres, Mongo, Redis, Qdrant)
