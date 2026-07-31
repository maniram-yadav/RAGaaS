"""Async SQLAlchemy engine/session wiring for the Postgres backend.

Connection details (host/port/db/user/password) are bootstrap-level config
(`.claude/rules/config-management.md`: "Environment variables — bootstrap/
infra-level settings (connection strings, ports)"), so they come from
`app.core.settings.Settings`, never from `ConfigService`/`system_config`.
`ConfigService` only ever tells callers *whether* Postgres is the active DB
backend (`system_config.db.active`), not how to connect to it.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import Settings, get_settings


def build_postgres_url(settings: Settings) -> str:
    """Build the `postgresql+asyncpg://` SQLAlchemy URL from bootstrap settings."""
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def create_postgres_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create a fresh async engine.

    Most callers should use the process-wide singleton via
    `get_postgres_sessionmaker()` instead; this is exposed separately for
    Alembic's `env.py` and tests that need an engine without a sessionmaker.
    """
    resolved = settings or get_settings()
    return create_async_engine(build_postgres_url(resolved), pool_pre_ping=True, future=True)


@lru_cache
def get_postgres_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide cached async session factory (Singleton-via-DI).

    Cached like `app.core.settings.get_settings`; tests that need to point at
    a different Postgres instance (e.g. a testcontainer) must call
    `get_postgres_sessionmaker.cache_clear()` (and `get_settings.cache_clear()`
    if settings were also monkeypatched) before resolving a fresh one.
    """
    engine = create_postgres_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
