"""
Tests for services/ratelimit.py — fixed-window limiting with the in-process
fallback (Redis path is exercised in production; fail-open behavior is what
matters here).
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException, Request

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services import ratelimit


@pytest.fixture(autouse=True)
def _isolated_limiter(monkeypatch):
    """Force the local counter path and start every test with a clean window."""
    monkeypatch.setattr("services.ratelimit.cache.get_redis", lambda: None)
    ratelimit._local.clear()
    yield
    ratelimit._local.clear()


def _request(ip: str = "9.9.9.9", forwarded: str = None) -> Request:
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    scope = {
        "type": "http", "method": "POST", "path": "/x", "headers": headers,
        "client": (ip, 1234), "query_string": b"",
    }
    return Request(scope)


# ── window mechanics ─────────────────────────────────────────────────────────

async def test_allows_up_to_limit_then_blocks():
    dep = ratelimit.rate_limit("t_scope", times=3, seconds=60)
    req = _request()
    for _ in range(3):
        await dep(req)  # within limit — no raise
    with pytest.raises(HTTPException) as exc:
        await dep(req)
    assert exc.value.status_code == 429


async def test_window_resets_after_expiry():
    dep = ratelimit.rate_limit("t_reset", times=1, seconds=60)
    req = _request()
    await dep(req)
    real = ratelimit.time.monotonic()
    with patch("services.ratelimit.time.monotonic", return_value=real + 61):
        await dep(req)  # new window — allowed again


async def test_limits_are_per_ip():
    dep = ratelimit.rate_limit("t_ip", times=1, seconds=60)
    await dep(_request(ip="1.1.1.1"))
    await dep(_request(ip="2.2.2.2"))  # different client, own budget
    with pytest.raises(HTTPException):
        await dep(_request(ip="1.1.1.1"))


async def test_uses_first_forwarded_ip_behind_proxy():
    dep = ratelimit.rate_limit("t_fwd", times=1, seconds=60)
    await dep(_request(ip="10.0.0.1", forwarded="203.0.113.7, 10.0.0.1"))
    with pytest.raises(HTTPException):
        # Same end client via the proxy — counted against 203.0.113.7.
        await dep(_request(ip="10.0.0.1", forwarded="203.0.113.7, 10.0.0.1"))


# ── per-user limits (OTP attempt caps) ───────────────────────────────────────

async def test_enforce_user_limit_blocks_after_cap():
    for _ in range(5):
        await ratelimit.enforce_user_limit("user-1", "otp_verify_test", 5, 600)
    with pytest.raises(HTTPException) as exc:
        await ratelimit.enforce_user_limit("user-1", "otp_verify_test", 5, 600)
    assert exc.value.status_code == 429


async def test_user_limits_are_per_user():
    await ratelimit.enforce_user_limit("user-a", "t_user", 1, 600)
    await ratelimit.enforce_user_limit("user-b", "t_user", 1, 600)  # own budget
    with pytest.raises(HTTPException):
        await ratelimit.enforce_user_limit("user-a", "t_user", 1, 600)


# ── fail-open ────────────────────────────────────────────────────────────────

async def test_broken_redis_falls_back_to_local_counter(monkeypatch):
    """A Redis outage must not disable limiting entirely, and must not raise."""

    class BrokenRedis:
        async def incr(self, *a, **k):
            raise RuntimeError("redis down")

        async def expire(self, *a, **k):
            raise RuntimeError("redis down")

    monkeypatch.setattr("services.ratelimit.cache.get_redis", lambda: BrokenRedis())
    dep = ratelimit.rate_limit("t_broken", times=1, seconds=60)
    await dep(_request())  # served via local fallback
    with pytest.raises(HTTPException):
        await dep(_request())  # local fallback still enforces the cap
