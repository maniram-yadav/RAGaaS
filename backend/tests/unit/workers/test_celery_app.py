"""Unit tests for STORY-014's Celery wiring — no real Redis, external calls
mocked (`.claude/rules/testing-standards.md`: "unit/ — one loader/provider/
handler in isolation, external calls mocked").

The full round-trip-through-a-real-broker proof lives in
`tests/integration/workers/test_celery_app.py`.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from app.core.settings import get_settings
from app.workers.celery_app import RETRY_KWARGS, DeadLetterTask, build_celery_app, celery_app, ping


def test_celery_app_uses_settings_redis_url_for_broker_and_backend() -> None:
    settings = get_settings()
    assert celery_app.conf.broker_url == settings.redis_url
    assert celery_app.conf.result_backend == settings.redis_url


def test_celery_app_acks_late_and_solo_pool_for_reliability_and_windows() -> None:
    """`task_acks_late` so a crashed worker redelivers the task instead of
    losing it; `solo` pool because prefork's `fork()` is unavailable on
    Windows (this team's dev environment)."""
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_pool == "solo"


def test_retry_kwargs_sourced_from_settings() -> None:
    settings = get_settings()
    assert RETRY_KWARGS["max_retries"] == settings.worker_task_max_retries
    assert RETRY_KWARGS["retry_backoff"] == settings.worker_task_retry_backoff_seconds
    assert RETRY_KWARGS["retry_backoff_max"] == settings.worker_task_retry_backoff_max_seconds
    assert RETRY_KWARGS["retry_jitter"] is True
    assert Exception in RETRY_KWARGS["autoretry_for"]


def test_build_celery_app_is_a_fresh_instance_each_call() -> None:
    """`build_celery_app` (not a cached singleton) so integration tests can
    rebuild it against a testcontainers Redis instance."""
    app_one = build_celery_app()
    app_two = build_celery_app()
    assert app_one is not app_two


def test_ping_task_registered_and_returns_pong() -> None:
    assert "ragaas.ping" in celery_app.tasks
    # Calling the task function directly executes it synchronously, without
    # a broker round-trip (that proof is the integration test's job).
    assert ping() == "pong"


def test_ping_task_uses_dead_letter_base_and_retry_kwargs() -> None:
    registered = celery_app.tasks["ragaas.ping"]
    assert isinstance(registered, DeadLetterTask)
    assert registered.max_retries == RETRY_KWARGS["max_retries"]


def test_dead_letter_task_on_failure_pushes_json_record_to_redis() -> None:
    settings = get_settings()
    fake_client = MagicMock()

    with patch("app.workers.celery_app.redis.Redis.from_url", return_value=fake_client):
        task = DeadLetterTask()
        task.name = "test.some_task"
        error = RuntimeError("boom")
        task.on_failure(error, "task-id-123", (1, 2), {"a": "b"}, None)

    fake_client.rpush.assert_called_once()
    key, payload = fake_client.rpush.call_args[0]
    assert key == settings.worker_dead_letter_redis_key
    record = json.loads(payload)
    assert record["task_id"] == "task-id-123"
    assert record["task_name"] == "test.some_task"
    assert "boom" in record["error"]
    fake_client.close.assert_called_once()


def test_dead_letter_task_on_failure_does_not_raise_when_redis_unavailable() -> None:
    """A dead-letter push failing (e.g. Redis briefly down) must not mask the
    task's original failure with a new, unrelated exception."""
    with patch(
        "app.workers.celery_app.redis.Redis.from_url", side_effect=ConnectionError("down")
    ):
        task = DeadLetterTask()
        task.name = "test.some_task"
        # Should not raise.
        task.on_failure(RuntimeError("boom"), "task-id-456", (), {}, None)
