"""
Tests for the cross-session LLM cache (services/cache.py + gemini cached wrappers).

Covers:
  - cache_get/cache_set round-trip via a fake Redis
  - generate_cached calls the real model only once for a repeated semantic key
  - embed_text_cached round-trips a vector and avoids a second live call
  - fail-open: a cache outage still returns a live result
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import fakeredis.aioredis

from services import cache, gemini


@pytest.fixture
async def fake_cache(monkeypatch):
    """Point services.cache at an in-memory fake Redis for the duration of a test."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(cache, "_client", client, raising=False)
    monkeypatch.setattr(cache, "_initialized", True, raising=False)
    monkeypatch.setattr(cache, "get_redis", lambda: client)
    yield client
    await client.flushall()


# ── cache.py round-trip ──────────────────────────────────────────────────────

async def test_cache_set_get_round_trip(fake_cache):
    await cache.cache_set("vera:test:k", json.dumps({"a": 1}), ttl_seconds=60)
    raw = await cache.cache_get("vera:test:k")
    assert json.loads(raw) == {"a": 1}


async def test_cache_get_miss_returns_none(fake_cache):
    assert await cache.cache_get("vera:test:absent") is None


async def test_cache_disabled_is_noop(monkeypatch):
    """With no client configured, get returns None and set does not raise."""
    monkeypatch.setattr(cache, "get_redis", lambda: None)
    await cache.cache_set("vera:test:x", "v", ttl_seconds=60)  # no-op
    assert await cache.cache_get("vera:test:x") is None


# ── generate_cached ──────────────────────────────────────────────────────────

async def test_generate_cached_calls_model_once_for_same_key(fake_cache):
    mock = AsyncMock(return_value="generated schemes")
    with patch.object(gemini, "generate", mock):
        first = await gemini.generate_cached("prompt A", "schemes:Mumbai:medium")
        second = await gemini.generate_cached("prompt B differs", "schemes:Mumbai:medium")

    assert first == second == "generated schemes"
    assert mock.await_count == 1  # second served from cache despite a different prompt


async def test_generate_cached_distinct_keys_call_model_twice(fake_cache):
    mock = AsyncMock(side_effect=["one", "two"])
    with patch.object(gemini, "generate", mock):
        a = await gemini.generate_cached("p", "schemes:Mumbai:medium")
        b = await gemini.generate_cached("p", "clinics:Delhi:high")

    assert (a, b) == ("one", "two")
    assert mock.await_count == 2


async def test_generate_cached_does_not_cache_invalid_output(fake_cache):
    """A generation that fails `validate` must not be cached — it would otherwise
    pin the fallback for the whole TTL. The next call regenerates instead."""
    import json as _json

    mock = AsyncMock(side_effect=["not json", '["ok"]'])
    with patch.object(gemini, "generate", mock):
        first = await gemini.generate_cached(
            "p", "schemes:Mumbai:medium", validate=_json.loads
        )
        second = await gemini.generate_cached(
            "p", "schemes:Mumbai:medium", validate=_json.loads
        )

    assert first == "not json"          # returned live, caller will fall back
    assert second == '["ok"]'           # regenerated, not served the bad value
    assert mock.await_count == 2        # bad output was never cached


async def test_generate_cached_valid_output_is_cached(fake_cache):
    import json as _json

    mock = AsyncMock(return_value='["ok"]')
    with patch.object(gemini, "generate", mock):
        first = await gemini.generate_cached("p", "schemes:X:low", validate=_json.loads)
        second = await gemini.generate_cached("p", "schemes:X:low", validate=_json.loads)

    assert first == second == '["ok"]'
    assert mock.await_count == 1        # valid output served from cache on the second call


async def test_generate_cached_fail_open_on_redis_outage(monkeypatch):
    """A Redis outage (client ops raise) must degrade to a live model call, not error."""

    class BrokenRedis:
        async def get(self, *a, **k):
            raise RuntimeError("redis down")

        async def set(self, *a, **k):
            raise RuntimeError("redis down")

    monkeypatch.setattr(cache, "get_redis", lambda: BrokenRedis())

    mock = AsyncMock(return_value="live result")
    with patch.object(gemini, "generate", mock):
        result = await gemini.generate_cached("prompt", "schemes:Mumbai:medium")

    assert result == "live result"
    assert mock.await_count == 1


# ── embed_text_cached ────────────────────────────────────────────────────────

async def test_embed_text_cached_round_trips_vector(fake_cache):
    vector = [0.1, 0.2, 0.3]
    mock = AsyncMock(return_value=vector)
    with patch.object(gemini, "embed_text", mock):
        first = await gemini.embed_text_cached("india cancer scheme")
        second = await gemini.embed_text_cached("india cancer scheme")

    assert first == second == vector
    assert mock.await_count == 1  # second hit comes from cache
