"""
Lightweight fixed-window rate limiting.

Backed by Redis (shared across workers) when REDIS_URL is set, with an
in-process fallback so limits still apply when running cache-less. Fail-open
by design, matching services/cache.py: a Redis error must never take a request
down, so on any failure we fall back to the local counter.

Note: the cache Redis runs allkeys-lru, so under memory pressure a counter can
be evicted early. That briefly relaxes a limit; it never blocks a legit user.
"""

import time

from fastapi import HTTPException, Request

from services import cache

# key -> (count, window_expires_at). Pruned opportunistically.
_local: dict[str, tuple[int, float]] = {}
_LOCAL_MAX_KEYS = 10_000


def _client_ip(request: Request) -> str:
    # Caddy fronts the app in production and sets X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _hit_local(key: str, times: int, seconds: int) -> bool:
    now = time.monotonic()
    if len(_local) > _LOCAL_MAX_KEYS:
        for k in [k for k, (_, exp) in _local.items() if exp < now]:
            _local.pop(k, None)
    count, expires = _local.get(key, (0, now + seconds))
    if now >= expires:
        count, expires = 0, now + seconds
    count += 1
    _local[key] = (count, expires)
    return count <= times


async def _hit(key: str, times: int, seconds: int) -> bool:
    """Record one hit against the window; True if still within the limit."""
    client = cache.get_redis()
    if client is not None:
        try:
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, seconds)
            return count <= times
        except Exception:
            pass  # fail open to the local counter
    return _hit_local(key, times, seconds)


def _reject() -> HTTPException:
    return HTTPException(
        status_code=429,
        detail="Too many requests. Please wait a moment and try again.",
    )


def rate_limit(scope: str, times: int, seconds: int):
    """FastAPI dependency: at most `times` requests per `seconds` per client IP."""

    async def dependency(request: Request) -> None:
        if not await _hit(f"vera:rl:{scope}:{_client_ip(request)}", times, seconds):
            raise _reject()

    return dependency


async def enforce_user_limit(user_id: str, scope: str, times: int, seconds: int) -> None:
    """Per-user limit for authenticated actions (e.g. OTP send/verify attempts)."""
    if not await _hit(f"vera:rl:{scope}:u:{user_id}", times, seconds):
        raise _reject()
