"""Shared fixtures for Postgres integration tests — a real Postgres via
`testcontainers`, migrated with Alembic, per `.claude/rules/testing-standards.md`
("integration/ — real Postgres/Mongo/Redis/Qdrant via testcontainers").

Engines/sessionmakers are deliberately built **per test function**, not
cached across the whole module: `pytest-asyncio` gives each `async def
test_*` its own event loop, and asyncpg connections/pools are bound to the
loop that created them. Reusing a module-scoped engine across tests running
on different loops surfaces as opaque `AttributeError`s deep in
`asyncio.proactor_events` on Windows — this fixture layout avoids that by
construction rather than pinning a loop scope.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer

from app.core.settings import get_settings
from app.infrastructure.db.postgres.session import create_postgres_engine, get_postgres_sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
MIGRATIONS_DIR = BACKEND_ROOT / "app" / "infrastructure" / "db" / "postgres" / "migrations"

_ENV_KEYS = ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")


@pytest.fixture(scope="module")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="module")
def _postgres_env(postgres_container: PostgresContainer) -> Iterator[None]:
    """Point bootstrap `Settings` at the running container and apply the
    Alembic migration once for the whole module.
    """
    original = {key: os.environ.get(key) for key in _ENV_KEYS}
    os.environ["POSTGRES_HOST"] = postgres_container.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = str(
        postgres_container.get_exposed_port(postgres_container.port)
    )
    os.environ["POSTGRES_USER"] = postgres_container.username
    os.environ["POSTGRES_PASSWORD"] = postgres_container.password
    os.environ["POSTGRES_DB"] = postgres_container.dbname

    get_settings.cache_clear()

    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    command.upgrade(alembic_cfg, "head")

    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


@pytest.fixture
async def postgres_sessionmaker(
    _postgres_env: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A fresh engine/sessionmaker bound to the current test's event loop."""
    engine = create_postgres_engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield sessionmaker
    finally:
        await engine.dispose()


@pytest.fixture
async def fresh_global_postgres_sessionmaker_cache(
    _postgres_env: None,
) -> AsyncIterator[None]:
    """Reset the process-wide `get_postgres_sessionmaker()` singleton so code
    that resolves it lazily (e.g. `RepositoryFactory`'s postgres builder)
    gets an engine bound to *this* test's event loop.
    """
    get_postgres_sessionmaker.cache_clear()
    try:
        yield
    finally:
        was_populated = get_postgres_sessionmaker.cache_info().currsize > 0
        if was_populated:
            await get_postgres_sessionmaker().kw["bind"].dispose()
        get_postgres_sessionmaker.cache_clear()
