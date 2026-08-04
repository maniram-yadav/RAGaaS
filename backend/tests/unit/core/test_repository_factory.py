"""Unit tests for `RepositoryFactory`'s registry-based resolution.

Uses fake `IUserRepository`/`IDocumentRepository` builders to prove the
Open/Closed acceptance criterion — "adding a new repository type requires
only a new registry entry" — without touching a real DB driver. The
end-to-end "real Postgres" proof lives in
`tests/integration/db/postgres/test_repository_factory.py`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

# Trigger "postgres" self-registration at import time (before the
# `_restore_registry`/`_restore_document_registry` autouse fixtures below take
# their baseline snapshot), so every test in this module starts from the same
# real registered state.
import app.infrastructure.db.postgres.document_repository  # noqa: E402,F401
import app.infrastructure.db.postgres.user_repository  # noqa: E402,F401
from app.core.config import ConfigService
from app.core.repository_factory import (
    DOCUMENT_REPOSITORY_REGISTRY,
    USER_REPOSITORY_REGISTRY,
    RepositoryFactory,
    register_document_repository,
    register_user_repository,
)


class _FakeUserRepository:
    """Stand-in satisfying the shape of `IUserRepository` for this test."""


class _FakeDocumentRepository:
    """Stand-in satisfying the shape of `IDocumentRepository` for this test."""


class _FakeConfigService(ConfigService):
    """A `ConfigService` whose "db" section is fixed, without needing Mongo."""

    def __init__(self, active: str) -> None:
        super().__init__(collection=None)
        self._active = active

    async def get(self, section: str) -> dict[str, Any]:
        if section == "db":
            return {"active": self._active}
        return await super().get(section)


@pytest.fixture(autouse=True)
def _restore_registry() -> Iterator[None]:
    original = dict(USER_REPOSITORY_REGISTRY)
    yield
    USER_REPOSITORY_REGISTRY.clear()
    USER_REPOSITORY_REGISTRY.update(original)


@pytest.fixture(autouse=True)
def _restore_document_registry() -> Iterator[None]:
    original = dict(DOCUMENT_REPOSITORY_REGISTRY)
    yield
    DOCUMENT_REPOSITORY_REGISTRY.clear()
    DOCUMENT_REPOSITORY_REGISTRY.update(original)


def test_postgres_is_registered_by_default() -> None:
    # Constructing a factory triggers self-registration of known backends.
    RepositoryFactory(config_service=_FakeConfigService(active="postgres"))

    assert "postgres" in USER_REPOSITORY_REGISTRY


def test_register_user_repository_is_purely_additive() -> None:
    """Registering a new backend must not disturb the existing "postgres" entry."""
    RepositoryFactory(config_service=_FakeConfigService(active="postgres"))
    postgres_builder_before = USER_REPOSITORY_REGISTRY["postgres"]

    @register_user_repository("fake")
    def _build_fake() -> _FakeUserRepository:
        return _FakeUserRepository()

    assert USER_REPOSITORY_REGISTRY["postgres"] is postgres_builder_before
    assert USER_REPOSITORY_REGISTRY["fake"] is _build_fake


@pytest.mark.asyncio
async def test_get_user_repository_dispatches_by_active_backend() -> None:
    @register_user_repository("fake")
    def _build_fake() -> _FakeUserRepository:
        return _FakeUserRepository()

    factory = RepositoryFactory(config_service=_FakeConfigService(active="fake"))

    repo = await factory.get_user_repository()

    assert isinstance(repo, _FakeUserRepository)


@pytest.mark.asyncio
async def test_get_user_repository_raises_for_unregistered_backend() -> None:
    factory = RepositoryFactory(config_service=_FakeConfigService(active="does-not-exist"))

    with pytest.raises(ValueError, match="does-not-exist"):
        await factory.get_user_repository()


def test_postgres_document_repository_is_registered_by_default() -> None:
    # Constructing a factory triggers self-registration of known backends.
    RepositoryFactory(config_service=_FakeConfigService(active="postgres"))

    assert "postgres" in DOCUMENT_REPOSITORY_REGISTRY


def test_register_document_repository_is_purely_additive() -> None:
    """Registering a new backend must not disturb the existing "postgres" entry."""
    RepositoryFactory(config_service=_FakeConfigService(active="postgres"))
    postgres_builder_before = DOCUMENT_REPOSITORY_REGISTRY["postgres"]

    @register_document_repository("fake")
    def _build_fake() -> _FakeDocumentRepository:
        return _FakeDocumentRepository()

    assert DOCUMENT_REPOSITORY_REGISTRY["postgres"] is postgres_builder_before
    assert DOCUMENT_REPOSITORY_REGISTRY["fake"] is _build_fake


@pytest.mark.asyncio
async def test_get_document_repository_dispatches_by_active_backend() -> None:
    @register_document_repository("fake")
    def _build_fake() -> _FakeDocumentRepository:
        return _FakeDocumentRepository()

    factory = RepositoryFactory(config_service=_FakeConfigService(active="fake"))

    repo = await factory.get_document_repository()

    assert isinstance(repo, _FakeDocumentRepository)


@pytest.mark.asyncio
async def test_get_document_repository_raises_for_unregistered_backend() -> None:
    factory = RepositoryFactory(config_service=_FakeConfigService(active="does-not-exist"))

    with pytest.raises(ValueError, match="does-not-exist"):
        await factory.get_document_repository()
