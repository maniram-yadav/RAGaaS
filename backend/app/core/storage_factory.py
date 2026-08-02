"""`StorageFactory` — resolves the active object-storage backend's `IStorageService`.

Reads `system_config.storage.active` through `ConfigService` (STORY-003) and
looks up the matching builder in a registry dict (Factory + Open/Closed),
mirroring `app.core.repository_factory.RepositoryFactory`'s established
pattern. A new storage backend (e.g. S3/GCS/Azure, STORY-046/STORY-047) is
added purely by:

1. A new module implementing `IStorageService` that calls
   `register_storage_service("s3")` on itself at import time.
2. One new entry in `_STORAGE_SERVICE_MODULES` below.

`StorageFactory`'s resolution logic (`get_storage_service`) never changes to
support a new backend — no `if/elif` branch is ever added there.

Unlike `RepositoryFactory`'s zero-arg builders (Postgres connection details
are bootstrap-only, never in `system_config`), a storage backend's *target*
(local base path, S3 bucket/region, ...) genuinely is a `system_config`
tunable (see `config/system_config.example.json`'s `storage.*` keys), so each
builder receives the resolved `storage` section and is responsible for
picking its own sub-section out of it.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from importlib import import_module
from typing import Any

from app.core.config import ConfigService, get_config_service
from app.domain.storage.service import IStorageService

StorageServiceBuilder = Callable[[dict[str, Any]], IStorageService]

#: backend name (matches `system_config.storage.active`) -> builder taking the
#: resolved `storage` section and returning an `IStorageService`.
STORAGE_SERVICE_REGISTRY: dict[str, StorageServiceBuilder] = {}


def register_storage_service(
    backend: str,
) -> Callable[[StorageServiceBuilder], StorageServiceBuilder]:
    """Decorator registering `builder` as the `IStorageService` factory for `backend`.

    Used by each concrete implementation module (e.g.
    `app.infrastructure.storage.local`) to self-register on import, keeping
    this module free of any infra imports itself.
    """

    def _decorator(builder: StorageServiceBuilder) -> StorageServiceBuilder:
        STORAGE_SERVICE_REGISTRY[backend] = builder
        return builder

    return _decorator


#: Modules that self-register an `IStorageService` builder as a side effect of
#: being imported. Open/Closed: adding a new storage backend is one new string
#: here (+ the new module itself) — never a change to `StorageFactory`.
_STORAGE_SERVICE_MODULES: tuple[str, ...] = (
    "app.infrastructure.storage.local",
)


def _ensure_registered() -> None:
    for module_name in _STORAGE_SERVICE_MODULES:
        import_module(module_name)


class StorageFactory:
    """Resolves an `IStorageService` for the currently-active storage backend."""

    def __init__(self, config_service: ConfigService | None = None) -> None:
        self._config_service = config_service or get_config_service()
        _ensure_registered()

    async def get_storage_service(self) -> IStorageService:
        """Return an `IStorageService` for `system_config.storage.active`.

        Raises:
            ValueError: if no storage service is registered for the active backend.
        """
        storage_section = await self._config_service.get("storage")
        active = storage_section.get("active", "local")
        try:
            builder = STORAGE_SERVICE_REGISTRY[active]
        except KeyError as exc:
            known = sorted(STORAGE_SERVICE_REGISTRY)
            raise ValueError(
                f"No storage service registered for storage backend {active!r}. "
                f"Known backends: {known}"
            ) from exc
        return builder(storage_section)


@lru_cache
def get_storage_factory() -> StorageFactory:
    """Return the process-wide cached `StorageFactory` (Singleton-via-DI)."""
    return StorageFactory()
