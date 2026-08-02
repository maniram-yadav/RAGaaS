# User repository

## Overview

Establishes the repository abstraction pattern used by every persistence-backed aggregate in RAGaaS,
with the `User` aggregate as its first (and so far only) concrete implementation. Implements plan
§4.9/§5's Dependency Inversion decision: business logic and API routers depend only on
`app.domain.users.repository.IUserRepository`, never on a concrete SQLAlchemy/Motor class, and the
active backend is resolved at runtime through a registry-based `RepositoryFactory` rather than
hardcoded imports. This is the template STORY-009 (Document), STORY-022 (Conversation/Message),
STORY-027 (TabularColumnProfile), STORY-045 (Mongo repos for all of the above), STORY-052/054 (Plan,
Subscription/Invoice) all copy.

## Interfaces / contracts

- `app.domain.users.entities.User` — framework-free dataclass entity: `id`, `email`,
  `hashed_password`, `name`, `role` (a `Role` enum as of STORY-006 — see
  [auth.md](auth.md) — subclassing `str` so it still compares/persists as a plain string), `org_id`
  (placeholder for the not-yet-built org/tenant model), `created_at`, `updated_at`.
- `app.domain.users.repository.IUserRepository` — ABC with `create`, `get_by_id`, `get_by_email`,
  `update`, `delete`, all `async`. Narrow by design (Interface Segregation): no query/list method is
  added until a story actually needs one.
- `app.domain.users.errors.UserAlreadyExistsError`, `UserNotFoundError` — stable domain-level
  exceptions every `IUserRepository` implementation must raise (not a driver-specific exception like
  `sqlalchemy.exc.IntegrityError`), so callers can catch one exception type regardless of active backend.
- `app.infrastructure.db.postgres.models.UserModel` — SQLAlchemy 2.0 `Mapped`/`mapped_column` ORM
  model for the `users` table (mirrors the plan's `User(id, email, hashed_password, name, role, org_id,
  created_at)` entity, plus `updated_at`).
- `app.infrastructure.db.postgres.base.Base` — shared `DeclarativeBase` every Postgres ORM model
  (this one, and later Document/Conversation/... models) maps onto.
- `app.infrastructure.db.postgres.session` — `build_postgres_url`, `create_postgres_engine`,
  `get_postgres_sessionmaker` (process-wide cached async session factory, built from bootstrap
  `Settings`, not `ConfigService` — connection details are bootstrap/infra-level, per
  `.claude/rules/config-management.md`).
- `app.infrastructure.db.postgres.user_repository.PostgresUserRepository` — the concrete
  `IUserRepository` implementation. Self-registers as the `"postgres"` backend builder on import.
- `app.core.repository_factory.RepositoryFactory` — resolves `system_config.db.active` via
  `ConfigService` and dispatches to the registered builder for that backend name.
  `get_repository_factory()` is the cached process-wide singleton accessor.
- `app.core.repository_factory.register_user_repository(backend: str)` /
  `USER_REPOSITORY_REGISTRY` — the registry decorator + dict. Adding a new DB backend (e.g. Mongo,
  STORY-045) is exactly: (1) a new module that implements `IUserRepository` and calls
  `register_user_repository("mongo")` on itself, and (2) one new string in
  `RepositoryFactory`'s `_USER_REPOSITORY_MODULES` tuple. `RepositoryFactory.get_user_repository()`'s
  resolution logic itself never changes (Open/Closed).
- Alembic migration `0001_create_users_table` under
  `app/infrastructure/db/postgres/migrations/versions/`, with `env.py` building its connection URL
  from `Settings` (never a hardcoded `sqlalchemy.url` in `alembic.ini`), and root `alembic.ini`
  pointing `script_location` at `app/infrastructure/db/postgres/migrations`.

## Config knobs

No new config keys were introduced by this story — it reuses:

- `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`
  (`.env.example`, bootstrap layer) — read by `app.core.settings.Settings` and turned into the
  SQLAlchemy async URL by `build_postgres_url`.
- `system_config.db.active` (default `"postgres"` via `DB_ACTIVE` in `.env.example`) — resolved
  through `ConfigService.get("db")` (STORY-003) and read by `RepositoryFactory.get_user_repository()`
  to pick the registered backend.

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule.

## Testing

- `backend/tests/unit/domain/users/` — `User` entity defaults/overrides, `IUserRepository`'s
  abstractness and exact method set, and the domain error types. No DB required.
- `backend/tests/unit/infrastructure/db/postgres/test_session.py` — `build_postgres_url` string
  construction, pure logic.
- `backend/tests/unit/core/test_repository_factory.py` — registry-based dispatch: `"postgres"` is
  registered by default, registering a new backend is purely additive (existing entries untouched),
  dispatch by `system_config.db.active`, and a clean `ValueError` for an unregistered backend. Uses a
  fake `IUserRepository`/`ConfigService`, no real DB.
- `backend/tests/integration/db/postgres/` — real Postgres via `testcontainers`
  (`postgres:16-alpine`), with the Alembic migration applied before each module's tests run:
  - `test_user_repository.py` — full CRUD round-trip (create → get_by_id/get_by_email → update →
    delete), duplicate-email and not-found error paths, against `PostgresUserRepository` directly.
  - `test_repository_factory.py` — `RepositoryFactory.get_user_repository()` returns a working
    `PostgresUserRepository` when `system_config.db.active == "postgres"` (verified by an actual
    create/get round trip through the factory-returned repo), and raises for an unknown backend.
  - Engines/sessionmakers are built per test function rather than cached module-wide, since
    `pytest-asyncio` gives each test its own event loop and asyncpg connections are bound to the loop
    that created them.

Run with (from `backend/`):

```
pytest tests/unit -q          # no external dependencies
pytest tests/integration -q   # requires Docker (testcontainers spins up postgres:16-alpine)
```

## Story references

- STORY-004 — `IUserRepository`/`PostgresUserRepository`/`RepositoryFactory` foundational
  implementation.
