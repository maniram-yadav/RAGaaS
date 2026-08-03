# Document model + repository

## Overview

Introduces the `Document` aggregate — the metadata record for every uploaded file — following the
repository pattern established by [user-repository.md](user-repository.md) (STORY-004). Implements
plan §6's `Document(id, org_id, filename, file_type, storage_uri, schema_json[nullable], status,
uploaded_by, created_at)` data model and a Postgres-backed `IDocumentRepository`. This is the
persistence foundation the upload endpoint (STORY-010), loaders (STORY-011+), and chunking pipeline
(STORY-015) build on: `status` tracks a document through `uploaded` → `processing` → `ready`/`failed`,
and `schema_json` is the slot the Excel/Csv loaders (STORY-026) populate for `tabular-qa-engineer`'s
downstream stories.

## Interfaces / contracts

- `app.domain.ingestion.entities.Document` — framework-free dataclass entity: `org_id`, `filename`,
  `file_type`, `storage_uri`, `uploaded_by` (a `UUID`, the uploading user's id), `id` (auto-generated
  `UUID`), `schema_json` (nullable free-form `dict`, populated only by tabular loaders), `status`
  (a `DocumentStatus`, defaults to `UPLOADED`), `created_at`.
- `app.domain.ingestion.entities.DocumentStatus` — `str`-subclassing `Enum` with `UPLOADED`,
  `PROCESSING`, `READY`, `FAILED` (mirrors `Role` in `app.domain.users.entities`: compares/persists as
  a plain string, so the Postgres `String(32)` column round-trips unchanged).
- `app.domain.ingestion.repository.IDocumentRepository` — ABC with `create`, `get_by_id`,
  `list_by_org`, `update_status`, `delete`, all `async`. `list_by_org` is the only multi-row method and
  every implementation must filter by `org_id` at the query level (no cross-tenant leakage).
- `app.domain.ingestion.errors.DocumentNotFoundError` — stable domain-level exception every
  `IDocumentRepository` implementation must raise from `update_status`/`delete` on an unknown id (not a
  driver-specific exception like `sqlalchemy.exc.NoResultFound`).
- `app.infrastructure.db.postgres.models.DocumentModel` — SQLAlchemy 2.0 `Mapped`/`mapped_column` ORM
  model for the `documents` table, added alongside `UserModel` in the same `models.py` (both map onto
  the shared `Base`, so Alembic autogenerate and `Base.metadata` see the whole schema from one import).
  `uploaded_by` is a real foreign key to `users.id`; `org_id` is indexed (not yet a foreign key — the
  org/tenant model doesn't exist yet, matching `UserModel.org_id`'s existing placeholder treatment).
- `app.infrastructure.db.postgres.document_repository.PostgresDocumentRepository` — the concrete
  `IDocumentRepository` implementation, built the same way as `PostgresUserRepository` (takes an
  `async_sessionmaker[AsyncSession]`, converts between `DocumentModel` rows and `Document` entities).
  Deliberately **not** self-registered into `app.core.repository_factory`'s registry yet —
  `RepositoryFactory.get_document_repository()` wiring is STORY-010's scope (the upload endpoint is the
  first consumer), not this story's.
- Alembic migration `0002_create_documents_table` under
  `app/infrastructure/db/postgres/migrations/versions/` (`down_revision = "0001"`), creating the
  `documents` table with an indexed `org_id`, a `documents.uploaded_by -> users.id` foreign key, and
  dropping both cleanly on `downgrade()`.

## Config knobs

No new config keys were introduced by this story — it reuses the same Postgres bootstrap settings as
`IUserRepository` (STORY-004):

- `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`
  (`.env.example`, bootstrap layer) — read by `app.core.settings.Settings` and turned into the
  SQLAlchemy async URL by `build_postgres_url`.

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule.
`system_config.db.active`/`RepositoryFactory` dispatch for documents is not wired up until STORY-010.

## Testing

- `backend/tests/unit/domain/ingestion/test_entities.py` — `Document` defaults (auto id, `status`
  defaults to `DocumentStatus.UPLOADED`, `schema_json` defaults to `None`), explicit overrides, and
  `DocumentStatus`'s four required values matching plain strings. No DB required.
- `backend/tests/unit/domain/ingestion/test_repository.py` — `IDocumentRepository`'s abstractness and
  exact five-method set (`create`, `get_by_id`, `list_by_org`, `update_status`, `delete`).
- `backend/tests/unit/domain/ingestion/test_errors.py` — `DocumentNotFoundError` carries the document
  id and a readable message.
- `backend/tests/integration/db/postgres/test_document_repository.py` — real Postgres via
  `testcontainers` (`postgres:16-alpine`), reusing STORY-004's `postgres_sessionmaker`/`_postgres_env`
  fixtures (Alembic migrated to `head`, so both `0001` and `0002` apply): full CRUD round trip
  (`create` → `get_by_id` → `update_status` → `delete`), `schema_json` persistence, `list_by_org`
  returning only the requesting org's documents (proves the multi-tenancy scoping requirement) and an
  empty list for an unknown org, and `DocumentNotFoundError` on `update_status`/`delete` of a missing
  id. A real `users` row is created first via `PostgresUserRepository` to satisfy `uploaded_by`'s
  foreign key.

Run with (from `backend/`):

```
pytest tests/unit -q          # no external dependencies
pytest tests/integration -q   # requires Docker (testcontainers spins up postgres:16-alpine)
```

## Story references

- STORY-009 — `Document`/`DocumentStatus` entity, `IDocumentRepository`, `PostgresDocumentRepository`,
  and the `0002_create_documents_table` Alembic migration.
