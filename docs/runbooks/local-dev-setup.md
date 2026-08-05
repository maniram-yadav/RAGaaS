# Local dev environment setup (STORY-008)

Brings up every infra dependency the backend needs — Postgres, MongoDB, Redis, Qdrant — with one
command, then points the backend at them.

## 1. Bring up infra

```
docker compose up -d
```

This starts four services, each with a healthcheck and a named volume so data survives container
restarts (`postgres_data`, `mongo_data`, `redis_data`, `qdrant_data`):

| Service | Image | Host port(s) | Healthcheck |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | `5432` | `pg_isready` |
| `mongo` | `mongo:7` | `27017` | `db.adminCommand('ping')` |
| `redis` | `redis:7-alpine` | `6379` | `redis-cli ping` |
| `qdrant` | `qdrant/qdrant:v1.11.0` | `6333` (REST), `6334` (gRPC) | TCP connect check on `6333` |

Check status:

```
docker compose ps
```

All four should show `healthy` within ~20 seconds of a cold start (`docker compose up -d` after a
`docker compose down -v`).

To tear down (and wipe volumes, e.g. to reset local data):

```
docker compose down -v
```

## 2. Configure the backend

```
cp .env.example .env
```

Then fill in any real secrets (`APP_SECRET_KEY`, `OPENAI_API_KEY`, ...) — never commit `.env`, and no
agent ever edits it. The `POSTGRES_*`/`MONGO_*`/`REDIS_URL`/`QDRANT_*` values in `.env.example` already
match `docker-compose.yml`'s defaults (including the local-dev-only `POSTGRES_PASSWORD=raas`), so a
straight copy connects with zero changes.

`Settings` (`backend/app/core/settings.py`) reads these at process bootstrap; `ConfigService`
(`backend/app/core/config.py`) layers `system_config` (stored in the `mongo` container started above) on
top of them. See [docs/reference/configuration.md](../reference/configuration.md).

## 3. Migrate and run

```
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --reload
```

`alembic upgrade head` applies the Postgres migrations (`app/infrastructure/db/postgres/migrations/`)
against the `postgres` container from step 1. `uvicorn` then serves the API on `http://localhost:8000`;
`GET /health` returns `200` once it's up.

## Troubleshooting

- **`docker compose up -d` shows a service stuck `starting` / never `healthy`**: `docker compose logs
  <service>` — most commonly a port already in use on the host.
- **Postgres port conflict (`5432` already bound)**: some machines run a native/other PostgreSQL install
  already listening on `5432`. Symptom: the container itself reports `healthy`, but the backend/`psql`
  gets `password authentication failed` because the connection is actually landing on the *other*
  Postgres, not the container. Fix: stop the conflicting local service, or override the host port for
  this compose stack only (`POSTGRES_PORT=15432 docker compose up -d`, and set the matching
  `POSTGRES_PORT` in your `.env`) — never change the container's *internal* port or `.env.example`'s
  documented default of `5432`.
- **`ImportError: cannot import name '_QUERY_OPTIONS' from 'pymongo.cursor'`**: `motor==3.5.1` uses a
  `pymongo.cursor` private API removed in `pymongo>=4.9`. `backend/requirements.txt` pins
  `pymongo==4.8.0` to stay under that ceiling — if you see this, your virtualenv has a newer `pymongo`
  installed some other way; reinstall with `pip install -r requirements.txt`.

## Verifying connectivity

There's no permanent test that spins up this exact compose stack (that's deliberate — `backend/tests/
integration/` uses ephemeral `testcontainers` instances per `.claude/rules/testing-standards.md`, and
STORY-060 adds a testcontainers-based CI sweep). To manually confirm the backend can reach all four
compose services, from `backend/` with the venv above active and `docker compose up -d` running:

```python
import asyncio
from app.infrastructure.db.postgres.session import create_postgres_engine
from sqlalchemy import text

async def check_postgres():
    engine = create_postgres_engine()
    async with engine.connect() as conn:
        assert (await conn.execute(text("SELECT 1"))).scalar() == 1
    await engine.dispose()

asyncio.run(check_postgres())
```

(similarly: `motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri).admin.command("ping")` for Mongo,
`redis.asyncio.from_url(settings.redis_url).ping()` for Redis, and `GET {QDRANT_URL}/` for Qdrant — all
resolve via `app.core.settings.get_settings()`).
