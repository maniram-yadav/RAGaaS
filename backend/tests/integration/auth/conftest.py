"""Shared fixtures for the auth integration tests — real Postgres + real Redis
via `testcontainers` (`.claude/rules/testing-standards.md`: "integration/ —
real Postgres/Mongo/Redis/Qdrant via testcontainers").

Mirrors `tests/integration/db/postgres/conftest.py`'s per-test-function
engine/sessionmaker layout (asyncpg connections are bound to the event loop
that created them) and extends it with a Redis client for the token
blacklist, built fresh per test for the same reason.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import redis.asyncio as redis
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.core.settings import get_settings
from app.infrastructure.auth.redis_token_blacklist import RedisTokenBlacklist
from app.infrastructure.db.postgres.session import create_postgres_engine
from app.infrastructure.db.postgres.user_repository import PostgresUserRepository

BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
MIGRATIONS_DIR = BACKEND_ROOT / "app" / "infrastructure" / "db" / "postgres" / "migrations"

_ENV_KEYS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "REDIS_URL",
    "APP_SECRET_KEY",
    "JWT_ALGORITHM",
)


@pytest.fixture(scope="module")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="module")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer() as container:
        yield container


@pytest.fixture(scope="module")
def _infra_env(
    postgres_container: PostgresContainer, redis_container: RedisContainer
) -> Iterator[None]:
    """Point bootstrap `Settings` at the running containers and migrate once."""
    original = {key: os.environ.get(key) for key in _ENV_KEYS}

    os.environ["POSTGRES_HOST"] = postgres_container.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = str(
        postgres_container.get_exposed_port(postgres_container.port)
    )
    os.environ["POSTGRES_USER"] = postgres_container.username
    os.environ["POSTGRES_PASSWORD"] = postgres_container.password
    os.environ["POSTGRES_DB"] = postgres_container.dbname

    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    os.environ["REDIS_URL"] = f"redis://{redis_host}:{redis_port}/0"

    os.environ["APP_SECRET_KEY"] = "integration-test-secret"
    os.environ["JWT_ALGORITHM"] = "HS256"

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
async def user_repository(_infra_env: None) -> AsyncIterator[PostgresUserRepository]:
    """A fresh `PostgresUserRepository` bound to the current test's event loop."""
    engine = create_postgres_engine()
    sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    try:
        yield PostgresUserRepository(sessionmaker)
    finally:
        await engine.dispose()


@pytest.fixture
async def token_blacklist(_infra_env: None) -> AsyncIterator[RedisTokenBlacklist]:
    """A fresh `RedisTokenBlacklist` bound to the current test's event loop."""
    client = redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        yield RedisTokenBlacklist(client)
    finally:
        await client.aclose()
