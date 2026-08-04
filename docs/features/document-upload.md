# Document upload endpoint

## Overview

Exposes the first HTTP surface over the ingestion domain: `POST /api/documents/upload` plus the basic
CRUD surface (`GET /api/documents`, `GET /api/documents/{id}`, `DELETE /api/documents/{id}`) from plan
§7. Implements STORY-010 on top of STORY-009's `Document`/`IDocumentRepository` and STORY-005's
`IStorageService`: an uploaded file is validated (extension allow-list + a magic-byte content sniff),
persisted through the active `IStorageService`, and recorded as a `Document` row via the active
`IDocumentRepository` — created documents stay in `DocumentStatus.UPLOADED` since background processing
(STORY-015) doesn't exist yet.

## Interfaces / contracts

- `app.api.documents` — the FastAPI router (`prefix="/api/documents"`), depending only on
  `IStorageService`/`IDocumentRepository` (resolved via `StorageFactory`/`RepositoryFactory`) and
  `ConfigService` — never a concrete storage/repository implementation (Dependency Inversion).
  - `POST /upload` — multipart upload; 201 with a `DocumentResponse` on success, `415` for a
    disallowed/mismatched file type, `413` for an oversized file.
  - `GET ""` — lists documents scoped to the caller's org.
  - `GET /{document_id}` — 404s (never leaking existence) for a document outside the caller's org.
  - `DELETE /{document_id}` — deletes the stored object then the metadata row; 404s the same way as
    `GET`; tolerates the storage object already being gone.
  - All routes are auth-gated via `get_current_user` (STORY-006).
- `app.domain.ingestion.upload_validation.validate_upload` — pure domain-layer function (no FastAPI
  dependency): validates extension against an allow-list, size against a max, and sniffs file content
  against its claimed extension via `_EXTENSION_SNIFFERS`, a registry dict keyed by extension
  (Open/Closed — a new extension's sniff rule is one new entry, never a branch).
- `app.domain.ingestion.errors.UnsupportedFileTypeError` / `FileTooLargeError` — new domain errors
  raised by `validate_upload` and translated to `415`/`413` in the router.
- `app.core.repository_factory` — extended with `DOCUMENT_REPOSITORY_REGISTRY` /
  `register_document_repository` / `RepositoryFactory.get_document_repository()`, mirroring the existing
  `IUserRepository` registry exactly (Open/Closed: a new DB backend for documents is one new
  self-registering module + one registry entry, never a branch in `RepositoryFactory`).
  `app.infrastructure.db.postgres.document_repository` self-registers `"postgres"` on import.

## Config knobs

- `system_config.ingestion.max_upload_size_bytes` (default `20971520`, 20 MiB) — max accepted upload
  size.
- `system_config.ingestion.allowed_extensions` (default `[".txt", ".pdf", ".docx", ".xlsx", ".csv"]`) —
  allow-listed extensions.
- `.env.example` fallback: `INGESTION_MAX_UPLOAD_SIZE_BYTES`, `INGESTION_ALLOWED_EXTENSIONS`.

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule.

## Testing

- `backend/tests/unit/domain/ingestion/test_upload_validation.py` — extension parsing, accepts
  well-formed text/PDF/docx content, rejects a disallowed extension, rejects no-extension filenames,
  rejects content that doesn't match its claimed extension, rejects an oversized file (and accepts one
  exactly at the limit), case-insensitive extension matching.
- `backend/tests/unit/core/test_repository_factory.py` — extended with the document-repository half of
  the registry: postgres registered by default, registration is purely additive, dispatch by active
  backend, and a clear `ValueError` for an unregistered backend.
- `backend/tests/integration/documents/test_upload_endpoint.py` — `httpx.AsyncClient` against a running
  FastAPI test app (real Postgres via testcontainers): upload → `GET /{id}` round trip, a disallowed
  file type and content/extension mismatch both 415, an oversized file 413s, an unauthenticated upload
  is rejected, `GET ""` is scoped to the caller, another user's document 404s on both `GET` and
  `DELETE` (never leaking existence), delete-then-get 404s, and an unknown document id 404s.

Run with (from `backend/`):

```
pytest tests/unit -q          # no external dependencies
pytest tests/integration -q   # requires Docker (testcontainers spins up postgres:16-alpine)
```

## Story references

- STORY-010 — `POST /api/documents/upload` + `GET`/`GET {id}`/`DELETE` CRUD surface,
  `validate_upload`, and the `IDocumentRepository` half of `RepositoryFactory`.
