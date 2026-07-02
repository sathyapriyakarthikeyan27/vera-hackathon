"""
Redis cache-aside layer for expensive, user-agnostic LLM results
(Agent 2 government schemes and clinic lookups, scheme-search embeddings).

Design notes:
  - Fail-open: any Redis error or timeout is treated as a cache miss / no-op so
    the cache can never break a request. A request always falls through to the
    live model on a miss or outage.
  - Optional: if REDIS_URL is unset the app runs cache-less (get returns None,
    set is a no-op). This keeps local/test environments zero-config.
  - Values are JSON strings; callers serialize their own payloads.
"""

import logging
import os
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_client: Optional[aioredis.Redis] = None
_initialized = False

# Short timeouts: the cache is a latency optimization, never a bottleneck.
# If Redis is slow we'd rather miss and call the model than block the request.
_SOCKET_TIMEOUT = 1.0


def get_redis() -> Optional[aioredis.Redis]:
    """Lazily build the Redis client. Returns None if REDIS_URL is not configured."""
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        logger.info("REDIS_URL not set — LLM cache disabled (running cache-less).")
        _client = None
        return None
    try:
        _client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=_SOCKET_TIMEOUT,
            socket_connect_timeout=_SOCKET_TIMEOUT,
        )
        logger.info("Redis LLM cache configured (%s).", url.split("@")[-1])
    except Exception as exc:
        logger.warning("Failed to configure Redis (%s) — cache disabled: %s", url, exc)
        _client = None
    return _client


async def ping() -> bool:
    """Best-effort connectivity check for startup logging. Never raises."""
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception as exc:
        logger.warning("Redis ping failed — cache will run fail-open: %s", exc)
        return False


async def cache_get(key: str) -> Optional[str]:
    """Return the cached JSON string for key, or None on miss / any error."""
    client = get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as exc:
        logger.warning("cache_get failed for %s (treating as miss): %s", key, exc)
        return None


async def cache_set(key: str, value: str, ttl_seconds: int) -> None:
    """Store a JSON string under key with a TTL. Best-effort — never raises."""
    client = get_redis()
    if client is None:
        return
    try:
        await client.set(key, value, ex=ttl_seconds)
    except Exception as exc:
        logger.warning("cache_set failed for %s (ignored): %s", key, exc)


async def close_redis() -> None:
    global _client, _initialized
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
    _client = None
    _initialized = False
