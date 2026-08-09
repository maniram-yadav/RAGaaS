"""Shared fixtures for the Celery worker integration tests — a real Redis
broker/backend via `testcontainers`, per `.claude/rules/testing-standards.md`
("integration/ — real Postgres/Mongo/Redis/Qdrant via testcontainers").
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator

import pytest
from celery import Celery
from testcontainers.redis import RedisContainer

from app.core.settings import get_settings
from app.workers import celery_app as celery_app_module

_ENV_KEYS = ("REDIS_URL",)


@pytest.fixture(scope="module")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer() as container:
        yield container


@pytest.fixture
def worker_celery_app(redis_container: RedisContainer) -> Iterator[Celery]:
    """Rebuild the real `app.workers.celery_app` module against the running
    Redis testcontainer and yield its `celery_app`.

    Reloads the actual production module (env var + `importlib.reload`)
    rather than constructing a parallel `Celery` instance by hand, so these
    tests exercise the real wiring — retry kwargs, `DeadLetterTask`,
    `ping` — not a copy of it. Mirrors the env-var-override-then-rebuild
    pattern already used by `tests/integration/db/postgres/conftest.py` and
    `tests/integration/auth/conftest.py`.
    """
    original = {key: os.environ.get(key) for key in _ENV_KEYS}
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    os.environ["REDIS_URL"] = f"redis://{host}:{port}/0"
    get_settings.cache_clear()

    importlib.reload(celery_app_module)

    try:
        yield celery_app_module.celery_app
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()
        importlib.reload(celery_app_module)
