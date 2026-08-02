"""Infrastructure-layer auth support (STORY-006): the Redis-backed JWT blacklist.

Kept minimal and self-contained per this story's scope — full Celery/Redis
worker infrastructure lands in STORY-014; this module only opens a thin
`redis.asyncio.Redis` client for the blacklist set.
"""
