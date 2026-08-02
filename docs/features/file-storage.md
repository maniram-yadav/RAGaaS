# File storage

## Overview

Establishes the file-storage abstraction used by every feature that persists raw file bytes (document
uploads first, STORY-010), with a local-disk implementation as the first (and so far only) concrete
backend. Implements plan §4.9/§5's Dependency Inversion/Open-Closed decisions for storage exactly as
`RepositoryFactory` (STORY-004) did for the DB layer: business logic and API routers depend only on
`app.domain.storage.service.IStorageService`, never on a concrete `LocalFsStorage`/`S3Storage`/...
class, and the active backend is resolved at runtime through a registry-based `StorageFactory` reading
`system_config.storage.active` via `ConfigService` (STORY-003). This is the template STORY-046
(`S3Storage`) and STORY-047 (`GcsStorage`, `AzureBlobStorage`) extend purely additively.

## Interfaces / contracts

- `app.domain.storage.service.IStorageService` — ABC with `save(filename, content) -> uri`,
  `read(uri) -> bytes`, `delete(uri) -> None`, `get_presigned_url(uri, expires_in_seconds=3600) -> str`,
  all `async`. `uri` is an opaque, backend-scoped token — callers must never parse or construct one
  themselves, only pass back whatever `save()` returned.
- `app.domain.storage.errors.StorageObjectNotFoundError` — stable domain-level exception every
  `IStorageService` implementation must raise for an unknown `uri` (not a driver-specific exception like
  `FileNotFoundError`/`botocore.exceptions.ClientError`), so callers can catch one exception type
  regardless of active backend.
- `app.infrastructure.storage.local.LocalFsStorage` — the concrete local-disk `IStorageService`.
  `save()` writes a new file named `<uuid4hex>_<sanitized-filename>` under a configurable `base_path`
  (created lazily if missing) and returns its absolute path as a `file://` URI
  (`pathlib.Path.as_uri()`, RFC 8089 — portable across Windows and POSIX; round-tripped back to a `Path`
  via `urllib.request.url2pathname`). The incoming `filename` is sanitized (directory components
  stripped) so a crafted value like `"../../etc/passwd"` can't escape `base_path`. File I/O runs off the
  event loop via `asyncio.to_thread`. Self-registers as the `"local"` backend builder on import.
  - **Documented `get_presigned_url()` behavior**: local storage has no HTTP layer in front of it, so
    there is no real time-limited "presigned URL" concept. After confirming the object exists, this
    implementation returns the same `file://` URI unchanged (a served-path stub) — callers running
    against local storage should not expect a browser-fetchable HTTP(S) URL from this method. STORY-046
    (`S3Storage`) and STORY-047 (`GcsStorage`/`AzureBlobStorage`) implement genuine expiring presigned
    URLs.
- `app.core.storage_factory.StorageFactory` — resolves `system_config.storage.active` via
  `ConfigService` and dispatches to the registered builder for that backend name, passing it the whole
  resolved `storage` section (unlike `RepositoryFactory`'s zero-arg builders: a storage backend's target
  — local base path, S3 bucket/region, ... — is itself a `system_config` tunable, not bootstrap-only
  connection info, so each builder picks its own sub-section out of what it's given).
  `get_storage_factory()` is the cached process-wide singleton accessor.
- `app.core.storage_factory.register_storage_service(backend: str)` / `STORAGE_SERVICE_REGISTRY` — the
  registry decorator + dict. Adding a new storage backend (e.g. S3, STORY-046) is exactly: (1) a new
  module that implements `IStorageService` and calls `register_storage_service("s3")` on itself, and
  (2) one new string in `StorageFactory`'s `_STORAGE_SERVICE_MODULES` tuple.
  `StorageFactory.get_storage_service()`'s resolution logic itself never changes (Open/Closed).

## Config knobs

No new config keys were introduced by this story — `storage.active` and `storage.local.base_path` were
already anticipated in `config/system_config.example.json` and `.env.example` by STORY-003:

- `system_config.storage.active` (default `"local"` via `STORAGE_ACTIVE` in `.env.example`) — resolved
  through `ConfigService.get("storage")` and read by `StorageFactory.get_storage_service()` to pick the
  registered backend.
- `system_config.storage.local.base_path` (default `./var/storage` via `LOCAL_STORAGE_BASE_PATH` in
  `.env.example`) — read by the `"local"` registry builder to construct `LocalFsStorage`.

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule.

## Testing

- `backend/tests/unit/domain/storage/test_service.py` — `IStorageService`'s abstractness and exact
  method set. No filesystem access.
- `backend/tests/unit/infrastructure/storage/test_local.py` — round-trip save→read→delete against a
  `tmp_path`, lazy `base_path` directory creation, unique `uri` per `save()` call even for the same
  filename, path-traversal sanitization, `StorageObjectNotFoundError` for read/delete/`get_presigned_url`
  of an unknown `uri`, and the documented `get_presigned_url` stub behavior (returns the same `file://`
  URI). No real project directory is touched.
- `backend/tests/unit/core/test_storage_factory.py` — registry-based dispatch: `"local"` is registered
  by default, registering a new backend is purely additive (existing entries untouched), dispatch by
  `system_config.storage.active` (including the `"local"` default when `active` is unset), a real
  `LocalFsStorage` resolved with the configured `base_path`, and a clean `ValueError` for an
  unregistered backend. Uses a fake `IStorageService`/`ConfigService`, no real filesystem/DB dependency
  beyond `tmp_path`.

Run with (from `backend/`):

```
pytest tests/unit -q   # no external dependencies
```

## Story references

- STORY-005 — `IStorageService`/`LocalFsStorage`/`StorageFactory` foundational implementation.
