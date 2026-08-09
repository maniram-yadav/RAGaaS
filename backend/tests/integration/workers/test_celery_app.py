"""Integration tests for STORY-014: Celery app wired to a real Redis broker/
result backend via testcontainers.

Covers both acceptance criteria:
- `ping` task round-trips through Redis and returns a result.
- Retry/backoff policy demonstrated on a task that fails once then succeeds.

Plus the dead-letter handling pattern (plan §12) on a task that exhausts its
retries — infra-level proof, not a domain task body (STORY-015+ scope).
"""

from __future__ import annotations

import json

import pytest
import redis as redis_sync
from celery import Celery
from celery.contrib.testing.worker import start_worker

from app.core.settings import get_settings
from app.workers.celery_app import DeadLetterTask


def test_ping_round_trips_through_redis(worker_celery_app: Celery) -> None:
    """AC1: `ping` task round-trips through the real Redis broker/backend
    and returns its result end-to-end via an embedded worker."""
    with start_worker(worker_celery_app, perform_ping_check=False):
        result = worker_celery_app.send_task("ragaas.ping")
        assert result.get(timeout=10) == "pong"


def test_task_retries_then_succeeds(worker_celery_app: Celery) -> None:
    """AC2: retry/backoff policy demonstrated on a task that fails once then
    succeeds on Celery's automatic retry."""
    attempts = {"count": 0}

    @worker_celery_app.task(
        name="test.retry_then_succeed",
        base=DeadLetterTask,
        autoretry_for=(RuntimeError,),
        retry_backoff=0.1,
        retry_backoff_max=1,
        retry_jitter=False,
        max_retries=3,
    )
    def _retry_then_succeed() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient failure - retry should recover")
        return "succeeded"

    with start_worker(worker_celery_app, perform_ping_check=False):
        result = worker_celery_app.send_task("test.retry_then_succeed")
        assert result.get(timeout=10) == "succeeded"

    assert attempts["count"] == 2, "task should have failed once, then succeeded on retry"


def test_task_exhausting_retries_is_dead_lettered(worker_celery_app: Celery) -> None:
    """Dead-letter handling pattern (plan §12): once a task's retries are
    exhausted, `DeadLetterTask.on_failure` records it on
    `WORKER_DEAD_LETTER_REDIS_KEY` instead of the failure being dropped."""

    @worker_celery_app.task(
        name="test.always_fails",
        base=DeadLetterTask,
        autoretry_for=(RuntimeError,),
        retry_backoff=0.1,
        retry_backoff_max=1,
        retry_jitter=False,
        max_retries=1,
    )
    def _always_fails() -> None:
        raise RuntimeError("permanent failure")

    settings = get_settings()
    client = redis_sync.Redis.from_url(settings.redis_url, decode_responses=True)
    client.delete(settings.worker_dead_letter_redis_key)

    with start_worker(worker_celery_app, perform_ping_check=False):
        result = worker_celery_app.send_task("test.always_fails")
        with pytest.raises(Exception):  # noqa: B017 - deliberately broad: any terminal task failure
            result.get(timeout=10)

    entries = client.lrange(settings.worker_dead_letter_redis_key, 0, -1)
    assert len(entries) >= 1
    payload = json.loads(entries[-1])
    assert payload["task_name"] == "test.always_fails"
    assert "permanent failure" in payload["error"]
