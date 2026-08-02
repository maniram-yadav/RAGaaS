"""Unit tests for `StorageFactory`'s registry-based resolution.

Mirrors `tests/unit/core/test_repository_factory.py`'s structure: a fake
`IStorageService` builder proves the Open/Closed acceptance criterion
("adding a new storage backend requires only a new registry entry"), and a
real `LocalFsStorage` proves the story's other acceptance criterion
("switching `system_config.storage.active` is read correctly by the
factory") without touching a real DB/network dependency.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# Trigger "local" self-registration at import time (before the
# `_restore_registry` autouse fixture below takes its baseline snapshot), so
# every test in this module starts from the same real registered state.
import app.infrastructure.storage.local  # noqa: E402,F401
from app.core.config import ConfigService
from app.core.storage_factory import (
    STORAGE_SERVICE_REGISTRY,
    StorageFactory,
    register_storage_service,
)
from app.infrastructure.storage.local import LocalFsStorage


class _FakeStorageService:
    """Stand-in satisfying the shape of `IStorageService` for this test."""


class _FakeConfigService(ConfigService):
    """A `ConfigService` whose "storage" section is fixed, without needing Mongo."""

    def __init__(self, storage_section: dict[str, Any]) -> None:
        super().__init__(collection=None)
        self._storage_section = storage_section

    async def get(self, section: str) -> dict[str, Any]:
        if section == "storage":
            return self._storage_section
        return await super().get(section)


@pytest.fixture(autouse=True)
def _restore_registry() -> Iterator[None]:
    original = dict(STORAGE_SERVICE_REGISTRY)
    yield
    STORAGE_SERVICE_REGISTRY.clear()
    STORAGE_SERVICE_REGISTRY.update(original)


def test_local_is_registered_by_default() -> None:
    # Constructing a factory triggers self-registration of known backends.
    StorageFactory(config_service=_FakeConfigService({"active": "local"}))

    assert "local" in STORAGE_SERVICE_REGISTRY


def test_register_storage_service_is_purely_additive() -> None:
    """Registering a new backend must not disturb the existing "local" entry."""
    StorageFactory(config_service=_FakeConfigService({"active": "local"}))
    local_builder_before = STORAGE_SERVICE_REGISTRY["local"]

    @register_storage_service("fake")
    def _build_fake(_section: dict[str, Any]) -> _FakeStorageService:
        return _FakeStorageService()

    assert STORAGE_SERVICE_REGISTRY["local"] is local_builder_before
    assert STORAGE_SERVICE_REGISTRY["fake"] is _build_fake


@pytest.mark.asyncio
async def test_get_storage_service_dispatches_by_active_backend() -> None:
    @register_storage_service("fake")
    def _build_fake(_section: dict[str, Any]) -> _FakeStorageService:
        return _FakeStorageService()

    factory = StorageFactory(config_service=_FakeConfigService({"active": "fake"}))

    service = await factory.get_storage_service()

    assert isinstance(service, _FakeStorageService)


@pytest.mark.asyncio
async def test_get_storage_service_raises_for_unregistered_backend() -> None:
    factory = StorageFactory(config_service=_FakeConfigService({"active": "does-not-exist"}))

    with pytest.raises(ValueError, match="does-not-exist"):
        await factory.get_storage_service()


@pytest.mark.asyncio
async def test_get_storage_service_resolves_local_with_configured_base_path(
    tmp_path: Path,
) -> None:
    """Proves `system_config.storage.active`/`storage.local.base_path` are
    actually read by the factory, not just the backend name.
    """
    factory = StorageFactory(
        config_service=_FakeConfigService(
            {"active": "local", "local": {"base_path": str(tmp_path)}}
        )
    )

    service = await factory.get_storage_service()

    assert isinstance(service, LocalFsStorage)
    assert service.base_path == tmp_path


@pytest.mark.asyncio
async def test_get_storage_service_defaults_active_to_local_when_unset() -> None:
    factory = StorageFactory(config_service=_FakeConfigService({}))

    service = await factory.get_storage_service()

    assert isinstance(service, LocalFsStorage)
