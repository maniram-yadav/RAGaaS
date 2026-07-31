"""`ConfigService` — the single resolver of the config precedence chain.

Precedence (plan §4.9/§6/§11, `.claude/rules/config-management.md`):

1. The `system_config` document in MongoDB — single source of truth for
   runtime-tunable settings (which DB/storage/LLM/payment/vector-store strategy
   is active, model params, limits). Changeable without a redeploy.
2. Environment variables — bootstrap/infra-level settings.
3. `.env` defaults — local-dev fallback.

Layers 2 and 3 are combined by `app.core.settings.Settings` (pydantic-settings
already resolves env-var-overrides-dotenv-overrides-field-default). `ConfigService`
only has to choose between "value came from Mongo" and "value came from
`Settings`".

Every later factory (`RepositoryFactory`, `StorageFactory`, `LLMProviderFactory`,
...) reads its active strategy through `ConfigService.get(section)` — never
by reading env vars or `system_config` directly (Dependency Inversion).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from app.core.settings import Settings, get_settings

#: Default filter used to locate the single `system_config` document.
DEFAULT_SYSTEM_CONFIG_FILTER: dict[str, Any] = {"_id": "system_config"}


class SystemConfigCollection(Protocol):
    """The narrow subset of a Motor collection `ConfigService` depends on.

    Kept as a `Protocol` (Interface Segregation) so unit tests can supply an
    in-memory fake instead of a real `AsyncIOMotorCollection`/Mongo instance.
    """

    async def find_one(self, filter_: dict[str, Any], /) -> dict[str, Any] | None: ...

    async def update_one(
        self, filter_: dict[str, Any], update: dict[str, Any], /, upsert: bool = False
    ) -> Any: ...


def _default_db_section(settings: Settings) -> dict[str, Any]:
    return {"active": settings.db_active}


def _default_storage_section(settings: Settings) -> dict[str, Any]:
    return {
        "active": settings.storage_active,
        "local": {"base_path": settings.local_storage_base_path},
        "s3": {"bucket": settings.aws_s3_bucket, "region": settings.aws_region},
        "gcs": {"bucket": settings.gcs_bucket},
        "azure": {"container": settings.azure_storage_container},
    }


def _default_llm_section(settings: Settings) -> dict[str, Any]:
    return {
        "active": settings.llm_active,
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "embedding_model": settings.llm_embedding_model,
    }


def _default_payment_section(settings: Settings) -> dict[str, Any]:
    return {"active": settings.payment_active}


def _default_vectorstore_section(settings: Settings) -> dict[str, Any]:
    return {"active": settings.vectorstore_active}


def _default_safety_section(settings: Settings) -> dict[str, Any]:
    return {
        "rate_limit": {"requests_per_minute": settings.safety_rate_limit_rpm},
        "moderation": {"active": settings.safety_moderation_active},
    }


#: Registry of section-name -> default-section-builder. Open/Closed: a new
#: `system_config` section is one new builder function + one registry entry,
#: never a branch added to `ConfigService` itself.
SECTION_DEFAULT_BUILDERS: dict[str, Callable[[Settings], dict[str, Any]]] = {
    "db": _default_db_section,
    "storage": _default_storage_section,
    "llm": _default_llm_section,
    "payment": _default_payment_section,
    "vectorstore": _default_vectorstore_section,
    "safety": _default_safety_section,
}


@dataclass(frozen=True)
class ConfigChangeEvent:
    """Emitted to listeners whenever `ConfigService.set()` changes a section."""

    section: str
    values: dict[str, Any]


ConfigChangeListener = Callable[[ConfigChangeEvent], Any]


class ConfigService:
    """Resolves and caches `system_config` sections per the precedence chain.

    One instance is wired at startup (Singleton-via-DI, see `get_config_service`)
    and shared by every factory that needs to know an active strategy. A short
    in-process TTL cache avoids hitting MongoDB on every request; `set()`
    invalidates the cache for the section it wrote and notifies subscribers
    (Observer/pub-sub stub — in-process only for now).
    """

    def __init__(
        self,
        collection: SystemConfigCollection | None,
        settings: Settings | None = None,
        cache_ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        document_filter: dict[str, Any] | None = None,
    ) -> None:
        """Create a `ConfigService`.

        Args:
            collection: The Mongo `system_config` collection (or a test double
                satisfying `SystemConfigCollection`). `None` disables the Mongo
                layer entirely — `get()` then always resolves from `Settings`.
            settings: Bootstrap settings providing layers 2/3. Defaults to the
                process-wide cached `Settings` via `get_settings()`.
            cache_ttl_seconds: How long a resolved section is cached before the
                next `get()` re-reads Mongo. Defaults to
                `settings.config_cache_ttl_seconds`. Explicitly configurable per
                the story's acceptance criteria.
            clock: Monotonic time source, injectable for tests (fake clocks).
            document_filter: Mongo filter used to locate the single
                `system_config` document. Defaults to `{"_id": "system_config"}`.
        """
        self._collection = collection
        self._settings = settings or get_settings()
        self._ttl = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else float(self._settings.config_cache_ttl_seconds)
        )
        self._clock = clock
        self._filter = document_filter or dict(DEFAULT_SYSTEM_CONFIG_FILTER)
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}
        self._listeners: list[ConfigChangeListener] = []

    @property
    def cache_ttl_seconds(self) -> float:
        """The configured TTL, in seconds, for cached sections."""
        return self._ttl

    def on_change(self, listener: ConfigChangeListener) -> None:
        """Register a listener invoked with a `ConfigChangeEvent` on every `set()`."""
        self._listeners.append(listener)

    def _notify(self, section: str, values: dict[str, Any]) -> None:
        # In-process Observer/pub-sub stub (plan §5). Listeners are invoked
        # synchronously and must not be coroutine functions — an async handler
        # that needs to await something should schedule its own task from
        # within a synchronous wrapper before registering it here. Cross-process
        # pub/sub is left to a later hardening story per this story's scope.
        event = ConfigChangeEvent(section=section, values=values)
        for listener in list(self._listeners):
            listener(event)

    def default_section(self, section: str) -> dict[str, Any]:
        """Build the layer-2/3 default for `section` from `Settings`.

        Returns an empty dict for sections with no registered default builder
        (i.e. sections this service doesn't know the bootstrap shape of).
        """
        builder = SECTION_DEFAULT_BUILDERS.get(section)
        if builder is None:
            return {}
        return builder(self._settings)

    def _cached(self, section: str) -> dict[str, Any] | None:
        entry = self._cache.get(section)
        if entry is None:
            return None
        value, fetched_at = entry
        if self._clock() - fetched_at > self._ttl:
            return None
        return value

    def _store_cache(self, section: str, value: dict[str, Any]) -> None:
        self._cache[section] = (value, self._clock())

    async def _read_mongo_section(self, section: str) -> dict[str, Any]:
        if self._collection is None:
            return {}
        document = await self._collection.find_one(self._filter)
        if not document:
            return {}
        value = document.get(section)
        if not isinstance(value, dict) or not value:
            return {}
        return value

    async def get(self, section: str) -> dict[str, Any]:
        """Resolve `section` per the precedence chain, using the TTL cache.

        Returns the Mongo `system_config[section]` value when present and
        non-empty; otherwise the layer-2/3 default built from `Settings`.
        """
        cached = self._cached(section)
        if cached is not None:
            return cached

        resolved = await self._read_mongo_section(section)
        if not resolved:
            resolved = self.default_section(section)

        self._store_cache(section, resolved)
        return resolved

    async def set(self, section: str, values: dict[str, Any]) -> None:
        """Persist `values` as `section` in the `system_config` document.

        Upserts the document, refreshes the cache immediately (so a subsequent
        `get()` in this process sees the new value without waiting out the
        TTL), and notifies any registered change listeners.
        """
        if self._collection is None:
            raise RuntimeError("ConfigService.set() requires a Mongo collection")

        await self._collection.update_one(
            self._filter, {"$set": {section: values}}, upsert=True
        )
        self._store_cache(section, values)
        self._notify(section, values)

    def invalidate(self, section: str | None = None) -> None:
        """Drop cached value(s) so the next `get()` re-reads Mongo.

        Args:
            section: Invalidate only this section; `None` clears the whole cache.
        """
        if section is None:
            self._cache.clear()
        else:
            self._cache.pop(section, None)


@lru_cache
def get_config_service() -> ConfigService:
    """Return the process-wide `ConfigService` singleton, wired from `Settings`.

    Lazily imports Motor so this module has no hard dependency on a Mongo
    driver being importable in contexts that only need the pure-Python
    `ConfigService`/`Settings` classes (e.g. certain unit tests).
    """
    from motor.motor_asyncio import AsyncIOMotorClient

    settings = get_settings()
    client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(settings.mongo_uri)
    collection = client[settings.mongo_db]["system_config"]
    return ConfigService(collection=collection, settings=settings)
