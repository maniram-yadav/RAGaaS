"""`RepositoryFactory` — resolves the active DB backend's repositories.

Reads `system_config.db.active` through `ConfigService` (STORY-003) and looks
up the matching builder in a registry dict (Factory + Open/Closed). A new DB
backend (e.g. Mongo, STORY-045) is added purely by:

1. A new module implementing `IUserRepository` that calls
   `register_user_repository("mongo")` on itself at import time.
2. One new entry in `_USER_REPOSITORY_MODULES` below.

`RepositoryFactory`'s resolution logic (`get_user_repository`) never changes
to support a new backend — no `if/elif` branch is ever added there.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from importlib import import_module

from app.core.config import ConfigService, get_config_service
from app.domain.ingestion.repository import IDocumentRepository
from app.domain.users.repository import IUserRepository

UserRepositoryBuilder = Callable[[], IUserRepository]

#: backend name (matches `system_config.db.active`) -> zero-arg builder.
USER_REPOSITORY_REGISTRY: dict[str, UserRepositoryBuilder] = {}


def register_user_repository(
    backend: str,
) -> Callable[[UserRepositoryBuilder], UserRepositoryBuilder]:
    """Decorator registering `builder` as the `IUserRepository` factory for `backend`.

    Used by each concrete implementation module (e.g.
    `app.infrastructure.db.postgres.user_repository`) to self-register on
    import, keeping this module free of any infra imports itself.
    """

    def _decorator(builder: UserRepositoryBuilder) -> UserRepositoryBuilder:
        USER_REPOSITORY_REGISTRY[backend] = builder
        return builder

    return _decorator


#: Modules that self-register a `IUserRepository` builder as a side effect of
#: being imported. Open/Closed: adding a new DB backend is one new string
#: here (+ the new module itself) — never a change to `RepositoryFactory`.
_USER_REPOSITORY_MODULES: tuple[str, ...] = (
    "app.infrastructure.db.postgres.user_repository",
)


DocumentRepositoryBuilder = Callable[[], IDocumentRepository]

#: backend name (matches `system_config.db.active`) -> zero-arg builder.
#: Mirrors `USER_REPOSITORY_REGISTRY` exactly (STORY-010, following STORY-004's
#: established pattern for a second repository family).
DOCUMENT_REPOSITORY_REGISTRY: dict[str, DocumentRepositoryBuilder] = {}


def register_document_repository(
    backend: str,
) -> Callable[[DocumentRepositoryBuilder], DocumentRepositoryBuilder]:
    """Decorator registering `builder` as the `IDocumentRepository` factory for `backend`.

    Used by each concrete implementation module (e.g.
    `app.infrastructure.db.postgres.document_repository`) to self-register on
    import, keeping this module free of any infra imports itself.
    """

    def _decorator(builder: DocumentRepositoryBuilder) -> DocumentRepositoryBuilder:
        DOCUMENT_REPOSITORY_REGISTRY[backend] = builder
        return builder

    return _decorator


#: Modules that self-register a `IDocumentRepository` builder as a side effect
#: of being imported. Open/Closed: adding a new DB backend is one new string
#: here (+ the new module itself) — never a change to `RepositoryFactory`.
_DOCUMENT_REPOSITORY_MODULES: tuple[str, ...] = (
    "app.infrastructure.db.postgres.document_repository",
)


def _ensure_registered() -> None:
    for module_name in _USER_REPOSITORY_MODULES:
        import_module(module_name)
    for module_name in _DOCUMENT_REPOSITORY_MODULES:
        import_module(module_name)


class RepositoryFactory:
    """Resolves repositories for the currently-active DB backend."""

    def __init__(self, config_service: ConfigService | None = None) -> None:
        self._config_service = config_service or get_config_service()
        _ensure_registered()

    async def get_user_repository(self) -> IUserRepository:
        """Return an `IUserRepository` for `system_config.db.active`.

        Raises:
            ValueError: if no repository is registered for the active backend.
        """
        db_section = await self._config_service.get("db")
        active = db_section.get("active", "postgres")
        try:
            builder = USER_REPOSITORY_REGISTRY[active]
        except KeyError as exc:
            known = sorted(USER_REPOSITORY_REGISTRY)
            raise ValueError(
                f"No user repository registered for db backend {active!r}. "
                f"Known backends: {known}"
            ) from exc
        return builder()

    async def get_document_repository(self) -> IDocumentRepository:
        """Return an `IDocumentRepository` for `system_config.db.active`.

        Raises:
            ValueError: if no repository is registered for the active backend.
        """
        db_section = await self._config_service.get("db")
        active = db_section.get("active", "postgres")
        try:
            builder = DOCUMENT_REPOSITORY_REGISTRY[active]
        except KeyError as exc:
            known = sorted(DOCUMENT_REPOSITORY_REGISTRY)
            raise ValueError(
                f"No document repository registered for db backend {active!r}. "
                f"Known backends: {known}"
            ) from exc
        return builder()


@lru_cache
def get_repository_factory() -> RepositoryFactory:
    """Return the process-wide cached `RepositoryFactory` (Singleton-via-DI)."""
    return RepositoryFactory()
