# Config service

## Overview

`ConfigService` is the single resolver of RAGaaS's config precedence chain (plan §4.9/§6/§11):
`system_config` document in MongoDB → environment variables → `.env` defaults. Every later
factory (`RepositoryFactory`, `StorageFactory`, `LLMProviderFactory`, `PaymentProviderFactory`, ...)
reads its active strategy and tunables through `ConfigService.get(section)` instead of touching Mongo,
env vars, or `system_config.example.json`'s shape directly — this is the Dependency Inversion seam that
lets every later story swap a backend/provider by adding a registry entry rather than editing existing
code. `ConfigService` also owns a short in-process TTL cache (so hot paths don't hit MongoDB on every
request) and a minimal in-process Observer/pub-sub stub so other components can react when an admin
changes a section via `ConfigService.set()` (the actual admin HTTP endpoint is out of this story's scope
— see STORY-050).

Bootstrap-level settings (DB connection strings, the JWT signing key, and the env/`.env` fallback
defaults for every `system_config` section) live in `app.core.settings.Settings`, a
`pydantic-settings`-based model. `pydantic-settings` itself collapses the plan's "environment
variables → `.env` defaults" layers into one resolution order (explicit env var beats a value from a
`.env` file beats the field default), so `ConfigService` only has to choose between "value came from
Mongo" and "value came from `Settings`".

## Interfaces / contracts

- `ConfigService` (`backend/app/core/config.py`) — `async get(section: str) -> dict`,
  `async set(section: str, values: dict) -> None`, `on_change(listener)`, `invalidate(section=None)`,
  `default_section(section)`, `cache_ttl_seconds` property.
- `ConfigChangeEvent` (`backend/app/core/config.py`) — dataclass `(section: str, values: dict)` passed
  to listeners registered via `ConfigService.on_change()`.
- `SystemConfigCollection` (`backend/app/core/config.py`) — narrow `Protocol` (Interface Segregation)
  describing the two Motor collection methods `ConfigService` needs (`find_one`, `update_one`), so tests
  can substitute an in-memory fake instead of a real Mongo collection.
- `SECTION_DEFAULT_BUILDERS` (`backend/app/core/config.py`) — registry dict mapping a `system_config`
  section name to a `Settings -> dict` builder function. Open/Closed: a new section is one new builder
  function + one registry entry, never a branch added to `ConfigService.get()`.
- `get_config_service()` (`backend/app/core/config.py`) — process-wide cached (`lru_cache`) factory that
  wires a real `AsyncIOMotorCollection` from `Settings` (Singleton-via-DI).
- `Settings` (`backend/app/core/settings.py`) — `pydantic-settings` `BaseSettings` subclass; one field
  per bootstrap env var / per-section fallback default.
- `get_settings()` (`backend/app/core/settings.py`) — process-wide cached (`lru_cache`) `Settings`
  singleton.

## Config knobs

`ConfigService.get(section)` resolves the `db`, `storage`, `llm`, `payment`, `vectorstore`, and `safety`
sections of `system_config`, plus the top-level `config_cache_ttl_seconds` cache TTL. Every key in those
sections, and the env vars that back their layer-2/3 fallback defaults (`DB_ACTIVE`, `STORAGE_ACTIVE`,
`LLM_ACTIVE`, `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_EMBEDDING_MODEL`, `PAYMENT_ACTIVE`,
`VECTORSTORE_ACTIVE`, `SAFETY_RATE_LIMIT_RPM`, `SAFETY_MODERATION_ACTIVE`, `CONFIG_CACHE_TTL_SECONDS`),
are documented in [docs/reference/configuration.md](../reference/configuration.md), which is the source
of truth for the full precedence rule and every key's purpose/default. `Settings` also carries the
purely bootstrap-level vars (`APP_*`, `POSTGRES_*`, `MONGO_URI`/`MONGO_DB`, `REDIS_URL`, `QDRANT_*`,
`JWT_*`) already listed there.

No secret/credential is ever read by `ConfigService` or written to `system_config` — provider API keys
and connection secrets stay in `Settings`/env vars only (plan §11).

## Testing

- Location: `backend/tests/unit/core/test_config.py`, `backend/tests/unit/core/test_settings.py`.
- Run with: `pytest backend/tests/unit/core -q` (or `pytest backend/tests -q` for the whole backend
  suite).
- Covers:
  - Precedence: `get("db")` returns the Mongo value when the `system_config` document has a non-empty
    `db` key; falls back to the `Settings`-derived default when the document lacks that key, the
    document doesn't exist at all, or no Mongo collection was configured; the fallback default itself
    reflects an env var override on `Settings` (via `FakeSystemConfigCollection`, an in-memory double
    satisfying `SystemConfigCollection`).
  - Registry-based defaults for every declared section (`db`, `storage`, `llm`, `payment`,
    `vectorstore`, `safety`) and an empty-dict result for an unregistered section name.
  - TTL cache: a value is reused within the configured TTL (no extra `find_one` call), expires and
    re-reads Mongo once the TTL has elapsed (driven by an injectable `FakeClock`, no real time.sleep),
    and the TTL itself is configurable per `ConfigService` instance / falls back to
    `Settings.config_cache_ttl_seconds`.
  - `set()` upserts the `system_config` document, refreshes the cache immediately (no stale read),
    raises `RuntimeError` when no collection is configured, and notifies every registered
    `on_change` listener with a `ConfigChangeEvent` (Observer/pub-sub stub).
  - `Settings`: field defaults, env-var overrides, and that explicit constructor kwargs (used by tests
    to pin values) beat env vars — all with `_env_file=None` so a developer's real local `.env`, if any,
    can never influence test results; `get_settings()` singleton identity.

## Story references

- STORY-003 — `ConfigService` + `Settings` + precedence/TTL-cache/Observer-stub unit tests.
