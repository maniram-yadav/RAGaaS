# Background worker infrastructure (Celery + Redis)

## Overview

Provides the Celery application every later background job (document processing/chunking in STORY-015,
embedding in STORY-016+) will host its task bodies on, per plan §12 ("Idempotent, retryable background
jobs (Celery + dead-letter queue) for ingestion resilience"). `app/workers/celery_app.py` wires a
`Celery` app to the same Redis instance STORY-006's `RedisTokenBlacklist` already connects to (shared
`REDIS_URL`, both broker and result backend), and establishes the retry/backoff/dead-letter conventions
every retryable task should follow. This story deliberately ships no domain task body — only the app
wiring, the conventions, and a trivial `ragaas.ping` task proving the wiring works end-to-end.

## Interfaces / contracts

- `build_celery_app() -> Celery` — factory function (not a cached singleton) that constructs the
  process-wide `Celery` app from `Settings.redis_url`. Deliberately not memoized so integration tests
  can rebuild it after pointing `REDIS_URL` at a testcontainers Redis instance.
- `celery_app` — the process-wide `Celery` app instance (`build_celery_app()` called once at import
  time). Domain task modules (STORY-015+) import this and decorate their task functions with
  `@celery_app.task(...)`.
- `RETRY_KWARGS: dict[str, Any]` — the retry/backoff kwargs every retryable task should be declared
  with: `autoretry_for=(Exception,)`, exponential `retry_backoff`/`retry_backoff_max` (jittered, from
  `Settings`), `max_retries`. A task calls a flaky external system (LLM API, object storage, a DB) by
  declaring `@celery_app.task(base=DeadLetterTask, **RETRY_KWARGS)`.
- `DeadLetterTask(Task)` — base `Task` class whose `on_failure` hook (fired exactly once by Celery, only
  on a task's *terminal* failure — i.e. after retries are exhausted or on a non-retryable exception, not
  on each individual retry) pushes a JSON record (`task_id`, `task_name`, `args`, `kwargs`, `error`) onto
  the `WORKER_DEAD_LETTER_REDIS_KEY` Redis list via `RPUSH`, so a later story/operator can inspect or
  replay it. If the Redis push itself fails (e.g. Redis briefly down), the exception is logged and
  swallowed rather than masking the task's original failure.
- `ping` task (`name="ragaas.ping"`) — trivial task returning `"pong"`, declared with
  `base=DeadLetterTask, **RETRY_KWARGS` like any future real task, proving the full wiring works.

Celery config set on `celery_app.conf`: `task_acks_late=True` +
`task_reject_on_worker_lost=True` (a crashed worker redelivers rather than silently drops the task),
`worker_prefetch_multiplier=1`, `worker_pool="solo"` (prefork's `fork()` is unavailable on Windows, this
team's dev environment — production workers may override via CLI `-P`), `result_expires=3600`,
`timezone="UTC"`/`enable_utc=True`.

## Config knobs

Bootstrap-only — read once from `Settings` at worker process import time, **not** routed through
`ConfigService`/`system_config` (Celery's default execution model is synchronous and there's no
established async-to-sync bridge in this codebase to read the Motor-backed `system_config` document from
inside a task or at worker startup; see `docs/reference/configuration.md`'s "Worker (Celery) config"
section for the full rationale):

- `REDIS_URL` — Celery broker + result backend (same variable STORY-006's token blacklist and rate
  limiting already use).
- `WORKER_TASK_MAX_RETRIES` (default `3`) — max retry attempts before a task is given up on.
- `WORKER_TASK_RETRY_BACKOFF_SECONDS` (default `1`) — base seconds for Celery's exponential
  `retry_backoff`.
- `WORKER_TASK_RETRY_BACKOFF_MAX_SECONDS` (default `60`) — cap on the exponential backoff delay.
- `WORKER_DEAD_LETTER_REDIS_KEY` (default `ragaas:dead_letter`) — Redis list tasks are `RPUSH`ed to once
  retries are exhausted.

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule and
the dedicated "Worker (Celery) config" section explaining this deliberate exception to the usual
`system_config` → env → `.env` layering.

## Testing

- **Unit** — `backend/tests/unit/workers/test_celery_app.py` (8 tests, no real Redis, external calls
  mocked): broker/backend URL sourced from `Settings`; `task_acks_late`/`solo` pool config; `RETRY_KWARGS`
  sourced from `Settings`; `build_celery_app()` returns a fresh instance each call; `ping` task is
  registered and callable directly; `ping` is declared with `DeadLetterTask` base + `RETRY_KWARGS`;
  `DeadLetterTask.on_failure` pushes the expected JSON record to the dead-letter Redis list (mocked
  client); `DeadLetterTask.on_failure` does not raise when Redis is unavailable.
  Run with: `cd backend && python -m pytest tests/unit/workers -v`
- **Integration** — `backend/tests/integration/workers/test_celery_app.py` (3 tests, real Redis via
  `testcontainers.redis.RedisContainer`, real embedded worker via
  `celery.contrib.testing.worker.start_worker`; `tests/integration/workers/conftest.py` reloads the real
  `app.workers.celery_app` module against the container's connection string so these tests exercise the
  actual production wiring, not a parallel copy):
  - `test_ping_round_trips_through_redis` — AC1: `ragaas.ping` sent via `send_task`, result fetched back
    through the real Redis broker/backend within 10s.
  - `test_task_retries_then_succeeds` — AC2: a task that raises on its first invocation and succeeds on
    its second, declared with the same `DeadLetterTask`/retry-kwargs pattern, is automatically retried
    by Celery and returns `"succeeded"`; asserts the task body ran exactly twice (one failure, one
    success).
  - `test_task_exhausting_retries_is_dead_lettered` — dead-letter pattern (plan §12): a task that always
    fails, once its `max_retries` is exhausted, has a JSON record on `WORKER_DEAD_LETTER_REDIS_KEY`
    containing its task name and error.
  Run with: `cd backend && python -m pytest tests/integration/workers -v` (requires Docker running
  locally; testcontainers pulls/starts a Redis container automatically).

Both acceptance criteria are proven by the integration suite; all 3 integration tests plus all 8 unit
tests pass, and the full existing backend unit suite (146 tests) is unaffected. `ruff check` and `mypy`
are clean on `app/workers/`.

## Story references

- STORY-014 — Background worker infrastructure (Celery + Redis)
