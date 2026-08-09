"""Celery application wiring for RAGaaS background workers (STORY-014).

This module is infrastructure only: it wires a `Celery` app to the shared
Redis instance (broker + result backend, same `REDIS_URL` STORY-006's
`RedisTokenBlacklist` already connects to — see
`app.infrastructure.auth.redis_token_blacklist.get_redis_client`) and
establishes the retry/backoff/dead-letter conventions every later background
task (ingestion, embedding, ...) should follow. It intentionally does not
define any domain task body — those land with the story that owns them
(chunking is STORY-015, embedding is STORY-016+).

Retry/backoff/dead-letter convention (plan §12: "Idempotent, retryable
background jobs (Celery + dead-letter queue) for ingestion resilience"):

- Every task that can fail transiently (calls an external system: LLM API,
  object storage, a DB) should be declared with `base=DeadLetterTask` and
  `**RETRY_KWARGS`, e.g.::

      @celery_app.task(name="ingestion.process_document", base=DeadLetterTask, **RETRY_KWARGS)
      def process_document(document_id: str) -> None: ...

  `RETRY_KWARGS` gives the task Celery's built-in `autoretry_for` +
  exponential `retry_backoff` (with jitter, to avoid a thundering herd of
  retries all firing at the same offset) up to `WORKER_TASK_MAX_RETRIES`
  attempts, tunable via `.env.example`/`Settings` (see
  `docs/reference/configuration.md`'s "Worker (Celery) config" section for
  why this is bootstrap-only rather than `ConfigService`-routed).
- Once a task exhausts its retries, Celery calls the task's `on_failure`
  hook exactly once with the terminal exception (retries raise `Retry`
  internally, which Celery does not treat as a failure — `on_failure` only
  fires on the final, non-retryable failure). `DeadLetterTask.on_failure`
  pushes a JSON record describing the failure onto the
  `WORKER_DEAD_LETTER_REDIS_KEY` Redis list instead of the failure being
  silently dropped, so a later story (or an operator) can inspect/replay it.

Bootstrap config only — this module reads `Settings` directly, not
`ConfigService`: Celery's default worker execution model is synchronous and
there is no established async-to-sync bridge in this codebase to read the
(Motor/async-backed) `system_config` document from inside a task or at
worker startup.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis
from celery import Celery, Task

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


def build_celery_app() -> Celery:
    """Build a `Celery` app wired to `Settings.redis_url` for broker+backend.

    A plain function (not a cached singleton) so integration tests can
    rebuild it after pointing `REDIS_URL` at a testcontainers Redis instance,
    mirroring `create_postgres_engine`'s per-test-construction pattern in
    `app.infrastructure.db.postgres.session`.
    """
    settings = get_settings()
    app = Celery("ragaas", broker=settings.redis_url, backend=settings.redis_url)
    app.conf.update(
        task_default_retry_delay=settings.worker_task_retry_backoff_seconds,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        # `solo` is the only pool that works without `fork()`, which Windows
        # (this team's dev environment, per `.claude/rules/testing-standards.md`
        # integration tests already dodging the same fork-on-Windows issue)
        # does not support; production workers may override via CLI `-P`.
        worker_pool="solo",
        result_expires=3600,
        timezone="UTC",
        enable_utc=True,
    )
    return app


#: Process-wide Celery app. Domain task modules (STORY-015+) import this and
#: decorate their task functions with `@celery_app.task(...)`.
celery_app = build_celery_app()

#: Retry/backoff kwargs every retryable task should be declared with (see the
#: module docstring's convention). Snapshotted from `Settings` once at import
#: time, matching `Settings`' own bootstrap-only philosophy — restart the
#: worker process to pick up a changed `WORKER_TASK_*` env var.
_settings = get_settings()
RETRY_KWARGS: dict[str, Any] = {
    "autoretry_for": (Exception,),
    "retry_backoff": _settings.worker_task_retry_backoff_seconds,
    "retry_backoff_max": _settings.worker_task_retry_backoff_max_seconds,
    "retry_jitter": True,
    "max_retries": _settings.worker_task_max_retries,
}


class DeadLetterTask(Task):
    """Base `Task` that dead-letters a task once its retries are exhausted.

    Subclass via `@celery_app.task(base=DeadLetterTask, **RETRY_KWARGS)`.
    Deliberately payload-agnostic (Open/Closed): it knows nothing about any
    specific task's arguments, only how to record that *some* task failed
    terminally.
    """

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Push a JSON failure record to the dead-letter Redis list.

        Called by Celery exactly once per task invocation that ends in a
        terminal (non-retryable, or retries-exhausted) failure.
        """
        super().on_failure(exc, task_id, args, kwargs, einfo)
        settings = get_settings()
        record = {
            "task_id": task_id,
            "task_name": self.name,
            "args": repr(args),
            "kwargs": repr(kwargs),
            "error": repr(exc),
        }
        try:
            client = redis.Redis.from_url(settings.redis_url)
            try:
                client.rpush(settings.worker_dead_letter_redis_key, json.dumps(record))
            finally:
                client.close()
        except Exception:
            logger.exception(
                "Failed to push task %s (%s) to dead-letter list %s",
                task_id,
                self.name,
                settings.worker_dead_letter_redis_key,
            )


@celery_app.task(name="ragaas.ping", base=DeadLetterTask, **RETRY_KWARGS)
def ping() -> str:
    """Trivial task proving the worker round-trips through Redis end-to-end."""
    return "pong"
