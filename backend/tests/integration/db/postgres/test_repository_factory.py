"""Integration test proving `RepositoryFactory.get_user_repository()` returns
a *working* `PostgresUserRepository` when `system_config.db.active ==
"postgres"` — the story's headline acceptance criterion, end to end against a
real Postgres container.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.config import ConfigService
from app.core.repository_factory import RepositoryFactory
from app.domain.users.entities import User
from app.infrastructure.db.postgres.user_repository import PostgresUserRepository


class _FixedDbConfigService(ConfigService):
    """A `ConfigService` whose "db" section is fixed to `active`, without Mongo."""

    def __init__(self, active: str) -> None:
        super().__init__(collection=None)
        self._active = active

    async def get(self, section: str) -> dict[str, Any]:
        if section == "db":
            return {"active": self._active}
        return await super().get(section)


@pytest.mark.asyncio
async def test_get_user_repository_returns_working_postgres_repo(
    fresh_global_postgres_sessionmaker_cache: None,
) -> None:
    factory = RepositoryFactory(config_service=_FixedDbConfigService(active="postgres"))

    repo = await factory.get_user_repository()

    assert isinstance(repo, PostgresUserRepository)

    # "working": prove it round-trips against the real DB, not just the right type.
    created = await repo.create(
        User(email="factory@example.com", hashed_password="x", name="Factory")
    )
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.email == "factory@example.com"


@pytest.mark.asyncio
async def test_get_user_repository_raises_for_unknown_backend() -> None:
    factory = RepositoryFactory(config_service=_FixedDbConfigService(active="not-a-real-backend"))

    with pytest.raises(ValueError, match="not-a-real-backend"):
        await factory.get_user_repository()
