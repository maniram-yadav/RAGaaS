"""Alembic environment for the Postgres backend.

Builds its connection URL from `app.core.settings.Settings` (bootstrap env
vars / `.env` defaults) rather than a hardcoded `sqlalchemy.url` in
`alembic.ini`, per `.claude/rules/config-management.md` — this file never
reads a real `.env`; `Settings` (pydantic-settings) does that resolution and
this module never sees the raw file.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.settings import get_settings

# Import every ORM model module so `Base.metadata` is fully populated before
# `target_metadata` is read below. Additive-only: a later story adding
# Document/Conversation/... models just needs its own `models.py` imported
# here alongside this one.
from app.infrastructure.db.postgres import models as _models  # noqa: F401
from app.infrastructure.db.postgres.base import Base
from app.infrastructure.db.postgres.session import build_postgres_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return build_postgres_url(get_settings())


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live DB using the async engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
