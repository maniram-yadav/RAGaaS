"""Unit tests for `app.core.config.ConfigService`.

Covers this story's acceptance criteria:
    - `ConfigService.get("db")` returns the Mongo value when present, else falls
      back to env, else the `.env` default.
    - The TTL cache is configurable and covered by a unit test with a fake clock.

A tiny in-memory fake stands in for the Motor collection (`SystemConfigCollection`
is a narrow `Protocol` specifically so this is possible without a real Mongo).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.config import ConfigChangeEvent, ConfigService
from app.core.settings import Settings


class FakeClock:
    """A manually-advanceable clock standing in for `time.monotonic`."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class FakeSystemConfigCollection:
    """Minimal async double for the one Mongo collection `ConfigService` uses."""

    def __init__(self, initial_document: dict[str, Any] | None = None) -> None:
        self.document: dict[str, Any] | None = (
            dict(initial_document) if initial_document is not None else None
        )
        self.find_one_calls = 0
        self.update_one_calls = 0

    async def find_one(self, filter_: dict[str, Any]) -> dict[str, Any] | None:
        self.find_one_calls += 1
        return dict(self.document) if self.document is not None else None

    async def update_one(
        self, filter_: dict[str, Any], update: dict[str, Any], upsert: bool = False
    ) -> None:
        self.update_one_calls += 1
        if self.document is None:
            if not upsert:
                raise AssertionError("update_one called without upsert on missing doc")
            self.document = {}
        self.document.update(update.get("$set", {}))


def _settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)


# --- Precedence ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_returns_mongo_value_when_present() -> None:
    collection = FakeSystemConfigCollection({"db": {"active": "mongo"}})
    service = ConfigService(collection=collection, settings=_settings(db_active="postgres"))

    result = await service.get("db")

    assert result == {"active": "mongo"}


@pytest.mark.asyncio
async def test_get_falls_back_to_env_default_when_mongo_missing_section() -> None:
    # Document exists (other sections configured) but has no "db" key at all.
    collection = FakeSystemConfigCollection({"llm": {"active": "openai"}})
    service = ConfigService(collection=collection, settings=_settings(db_active="postgres"))

    result = await service.get("db")

    assert result == {"active": "postgres"}


@pytest.mark.asyncio
async def test_get_falls_back_to_env_default_when_document_missing_entirely() -> None:
    collection = FakeSystemConfigCollection(initial_document=None)
    service = ConfigService(collection=collection, settings=_settings(db_active="postgres"))

    result = await service.get("db")

    assert result == {"active": "postgres"}


@pytest.mark.asyncio
async def test_get_falls_back_to_settings_default_when_no_collection_configured() -> None:
    service = ConfigService(collection=None, settings=_settings(db_active="postgres"))

    result = await service.get("db")

    assert result == {"active": "postgres"}


@pytest.mark.asyncio
async def test_env_default_reflects_settings_env_var_override() -> None:
    """The ".env default" layer itself resolves via Settings' own env precedence."""
    collection = FakeSystemConfigCollection(initial_document=None)
    service = ConfigService(collection=collection, settings=_settings(db_active="mongo"))

    result = await service.get("db")

    assert result == {"active": "mongo"}


@pytest.mark.asyncio
async def test_unknown_section_with_no_mongo_value_resolves_to_empty_dict() -> None:
    collection = FakeSystemConfigCollection(initial_document={})
    service = ConfigService(collection=collection, settings=_settings())

    result = await service.get("not-a-real-section")

    assert result == {}


@pytest.mark.asyncio
async def test_storage_section_default_reflects_settings() -> None:
    collection = FakeSystemConfigCollection(initial_document=None)
    settings = _settings(storage_active="s3", aws_s3_bucket="my-bucket", aws_region="us-east-1")
    service = ConfigService(collection=collection, settings=settings)

    result = await service.get("storage")

    assert result["active"] == "s3"
    assert result["s3"] == {"bucket": "my-bucket", "region": "us-east-1"}


# --- TTL cache -------------------------------------------------------------


@pytest.mark.asyncio
async def test_cached_value_is_reused_within_ttl() -> None:
    collection = FakeSystemConfigCollection({"db": {"active": "mongo"}})
    clock = FakeClock()
    service = ConfigService(
        collection=collection, settings=_settings(), cache_ttl_seconds=30, clock=clock
    )

    first = await service.get("db")
    clock.advance(10)  # well within the 30s TTL
    second = await service.get("db")

    assert first == second == {"active": "mongo"}
    assert collection.find_one_calls == 1


@pytest.mark.asyncio
async def test_cache_expires_and_refreshes_after_ttl() -> None:
    collection = FakeSystemConfigCollection({"db": {"active": "mongo"}})
    clock = FakeClock()
    service = ConfigService(
        collection=collection, settings=_settings(), cache_ttl_seconds=30, clock=clock
    )

    await service.get("db")
    assert collection.find_one_calls == 1

    # Mutate the underlying "Mongo" doc directly (simulating another process
    # changing config) to prove the second get() actually re-reads it.
    collection.document["db"] = {"active": "postgres"}

    clock.advance(31)  # past the TTL
    refreshed = await service.get("db")

    assert refreshed == {"active": "postgres"}
    assert collection.find_one_calls == 2


@pytest.mark.asyncio
async def test_cache_ttl_is_configurable() -> None:
    collection = FakeSystemConfigCollection({"db": {"active": "mongo"}})
    clock = FakeClock()
    service = ConfigService(
        collection=collection, settings=_settings(), cache_ttl_seconds=5, clock=clock
    )

    await service.get("db")
    clock.advance(6)  # past the shorter 5s TTL
    await service.get("db")

    assert collection.find_one_calls == 2
    assert service.cache_ttl_seconds == 5


@pytest.mark.asyncio
async def test_default_ttl_comes_from_settings_when_not_overridden() -> None:
    service = ConfigService(collection=None, settings=_settings(config_cache_ttl_seconds=42))

    assert service.cache_ttl_seconds == 42


def test_invalidate_clears_cache_for_one_or_all_sections() -> None:
    service = ConfigService(collection=None, settings=_settings())
    service._store_cache("db", {"active": "postgres"})  # noqa: SLF001 - white-box cache test
    service._store_cache("llm", {"active": "openai"})  # noqa: SLF001

    service.invalidate("db")
    assert service._cached("db") is None  # noqa: SLF001
    assert service._cached("llm") is not None  # noqa: SLF001

    service.invalidate()
    assert service._cached("llm") is None  # noqa: SLF001


# --- set() + Observer/pub-sub ------------------------------------------------


@pytest.mark.asyncio
async def test_set_upserts_document_and_refreshes_cache_immediately() -> None:
    collection = FakeSystemConfigCollection(initial_document=None)
    clock = FakeClock()
    service = ConfigService(
        collection=collection, settings=_settings(), cache_ttl_seconds=30, clock=clock
    )

    await service.set("db", {"active": "mongo"})

    assert collection.document == {"db": {"active": "mongo"}}
    # No extra find_one hit needed: set() populates the cache directly.
    result = await service.get("db")
    assert result == {"active": "mongo"}
    assert collection.find_one_calls == 0


@pytest.mark.asyncio
async def test_set_without_collection_raises() -> None:
    service = ConfigService(collection=None, settings=_settings())

    with pytest.raises(RuntimeError):
        await service.set("db", {"active": "mongo"})


@pytest.mark.asyncio
async def test_set_notifies_registered_listeners() -> None:
    collection = FakeSystemConfigCollection(initial_document=None)
    service = ConfigService(collection=collection, settings=_settings())
    received: list[ConfigChangeEvent] = []
    service.on_change(received.append)

    await service.set("llm", {"active": "anthropic"})

    assert len(received) == 1
    assert received[0].section == "llm"
    assert received[0].values == {"active": "anthropic"}


@pytest.mark.asyncio
async def test_multiple_listeners_all_notified() -> None:
    collection = FakeSystemConfigCollection(initial_document=None)
    service = ConfigService(collection=collection, settings=_settings())
    calls_a: list[ConfigChangeEvent] = []
    calls_b: list[ConfigChangeEvent] = []
    service.on_change(calls_a.append)
    service.on_change(calls_b.append)

    await service.set("payment", {"active": "stripe"})

    assert len(calls_a) == 1
    assert len(calls_b) == 1
