"""`RedisTokenBlacklist` — a thin `redis-py` client backing JWT logout/rotation
revocation.

Deliberately minimal per STORY-006's scope note: "Redis wiring itself can be
a thin client here; full Celery/Redis infra lands in a later story
(STORY-014)". Each blacklisted `jti` is stored as its own key with a TTL equal
to the token's remaining lifetime, so entries self-expire and the set never
grows unbounded.
"""

from __future__ import annotations

from functools import lru_cache

import redis.asyncio as redis

from app.core.settings import get_settings

_KEY_PREFIX = "auth:blacklist:"


class RedisTokenBlacklist:
    """`ITokenBlacklist`-shaped (structural) Redis-backed JWT revocation set."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def blacklist(self, jti: str, ttl_seconds: int) -> None:
        """Mark `jti` as revoked for at least `ttl_seconds`.

        `ttl_seconds` should be the token's remaining lifetime so the key
        expires no later than the token itself would anyway.
        """
        if ttl_seconds <= 0:
            return
        await self._client.set(f"{_KEY_PREFIX}{jti}", "1", ex=ttl_seconds)

    async def is_blacklisted(self, jti: str) -> bool:
        """Return whether `jti` has been revoked."""
        return bool(await self._client.exists(f"{_KEY_PREFIX}{jti}"))


@lru_cache
def get_redis_client() -> redis.Redis:
    """Return the process-wide cached async Redis client (Singleton-via-DI).

    Like `get_postgres_sessionmaker`, tests that point at a different Redis
    instance (e.g. a testcontainer) must call `get_redis_client.cache_clear()`
    (and `get_settings.cache_clear()` if settings were also monkeypatched)
    before resolving a fresh one.
    """
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_token_blacklist() -> RedisTokenBlacklist:
    """Return the process-wide cached `RedisTokenBlacklist` (Singleton-via-DI)."""
    return RedisTokenBlacklist(get_redis_client())
