"""
Google Gemini service client.
Uses google-generativeai SDK (google-generativeai==0.8.3).

Model constants:
  GEMINI_FLASH = "gemini-2.5-flash"   — all agents except Agent 3
  GEMINI_PRO   = "gemini-2.5-pro"     — Agent 3 (document analysis, clinical signal extraction)
"""

import asyncio
import hashlib
import json
import logging
import os
from typing import Callable, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

_configured = False

GEMINI_FLASH = "gemini-2.5-flash"
GEMINI_PRO = "gemini-2.5-pro"

_RETRY_DELAYS = [5, 15]  # seconds to wait on 429 before each retry

# TTLs for the cross-session LLM cache (see services/cache.py).
CACHE_TTL_GENERATE = 7 * 24 * 3600   # scheme/clinic results are stable for days
CACHE_TTL_EMBED = 30 * 24 * 3600     # text -> embedding never changes for the same text


def _is_rate_limit(exc: Exception) -> bool:
    return "429" in str(exc)


def _configure() -> None:
    global _configured
    if not _configured:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            logger.warning(
                "GEMINI_API_KEY is not set — all Gemini calls will use static fallbacks. "
                "Add GEMINI_API_KEY=<your_key> to backend/.env and restart the server."
            )
            return
        genai.configure(api_key=key)
        _configured = True
        logger.info("Gemini API configured (flash: %s, pro: %s).", GEMINI_FLASH, GEMINI_PRO)


def validate_key_on_startup() -> None:
    """Call once at startup to surface missing API key immediately."""
    _configure()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        logger.error(
            "STARTUP: GEMINI_API_KEY is missing. "
            "Open backend/.env and set: GEMINI_API_KEY=AIza..."
        )
    else:
        logger.info(
            "STARTUP: GEMINI_API_KEY is present (length=%d). Flash: %s, Pro: %s.",
            len(key), GEMINI_FLASH, GEMINI_PRO,
        )


async def _generate_with_retry(model_obj, content, **kwargs) -> str:
    """Call generate_content_async with automatic retry on 429 rate limit."""
    last_exc: Exception = RuntimeError("unknown error")
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            logger.warning(
                "Gemini 429 rate limit — waiting %ds before retry %d/%d...",
                delay, attempt, len(_RETRY_DELAYS),
            )
            await asyncio.sleep(delay)
        try:
            response = await model_obj.generate_content_async(content, **kwargs)
            return response.text.strip()
        except Exception as exc:
            last_exc = exc
            if not _is_rate_limit(exc):
                raise
    raise last_exc


async def generate(prompt: str, model: str = GEMINI_FLASH) -> str:
    _configure()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is not set — add it to backend/.env")
    m = genai.GenerativeModel(model)
    return await _generate_with_retry(m, prompt)


async def generate_safe(
    prompt: str,
    fallback: str,
    model: str = GEMINI_FLASH,
) -> str:
    """Like generate() but returns fallback text on any error — never raises."""
    try:
        return await generate(prompt, model)
    except Exception as exc:
        logger.warning("Gemini generate_safe failed (model=%s): %s", model, exc)
        return fallback


async def generate_multimodal(parts: list, model: str = GEMINI_FLASH) -> str:
    """Send a multimodal prompt (text + inline file data) to Gemini."""
    _configure()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is not set")
    m = genai.GenerativeModel(model)
    return await _generate_with_retry(m, parts)


async def generate_multimodal_safe(
    parts: list,
    fallback: str,
    model: str = GEMINI_FLASH,
) -> str:
    try:
        return await generate_multimodal(parts, model)
    except Exception as exc:
        logger.warning("Gemini generate_multimodal_safe failed (model=%s): %s", model, exc)
        return fallback


async def generate_pro_multimodal(parts: list) -> str:
    """Document and image analysis using Gemini 2.5 Pro (Agent 3)."""
    return await generate_multimodal(parts, model=GEMINI_PRO)


async def generate_pro_multimodal_safe(parts: list, fallback: str) -> str:
    try:
        return await generate_pro_multimodal(parts)
    except Exception as exc:
        logger.warning("Gemini Pro multimodal failed: %s", exc)
        return fallback


async def embed_text(text: str, model: str = "models/embedding-001") -> list[float]:
    """Generate a 768-dimensional embedding for the given text."""
    _configure()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is not set")
    result = await asyncio.to_thread(genai.embed_content, model=model, content=text)
    return result["embedding"]


# ── Cross-session cache wrappers (cache-aside via Redis) ────────────────────────
# Opt-in only — used for user-agnostic results (Agent 2 schemes/clinics, embeddings).
# Never cache personalized output (companion chat, risk reasoning, records).


def _cache_key(namespace: str, model: str, semantic: str) -> str:
    digest = hashlib.sha256(f"{model}|{semantic}".encode("utf-8")).hexdigest()
    return f"vera:{namespace}:{digest}"


def _passes(validate: Optional[Callable[[str], object]], value: str) -> bool:
    """True if `value` is acceptable to cache/serve. No validator means accept all."""
    if validate is None:
        return True
    try:
        validate(value)
        return True
    except Exception:
        return False


async def generate_cached(
    prompt: str,
    semantic_key: str,
    *,
    model: str = GEMINI_FLASH,
    ttl: int = CACHE_TTL_GENERATE,
    validate: Optional[Callable[[str], object]] = None,
) -> str:
    """
    generate() with a Redis cache-aside layer.

    The cache is keyed by `semantic_key` (a coarse, user-agnostic descriptor like
    "clinics:Mumbai:colorectal:Gastroenterologist") rather than the full prompt, so
    per-user personalization in the prompt does not fragment the cache. Fail-open:
    a cache outage simply means a live call.

    `validate`, if given, is called on the model output before it is cached and on
    any cached value before it is served. Only values that pass are stored, so a
    single malformed generation cannot poison the key for the whole TTL. A cached
    value that fails validation (e.g. written before a validator existed) is treated
    as a miss and regenerated. Validators must raise on bad input.
    """
    from services import cache  # local import keeps gemini.py free of import-time coupling

    key = _cache_key("llm", model, semantic_key)
    hit = await cache.cache_get(key)
    if hit is not None:
        if _passes(validate, hit):
            logger.info("llm_cache HIT %s", semantic_key)
            return hit
        logger.info("llm_cache STALE %s (cached value failed validation) — regenerating", semantic_key)
    else:
        logger.info("llm_cache MISS %s", semantic_key)

    result = await generate(prompt, model)
    if _passes(validate, result):
        await cache.cache_set(key, result, ttl)
    return result


async def embed_text_cached(
    text: str,
    *,
    model: str = "models/embedding-001",
    ttl: int = CACHE_TTL_EMBED,
) -> list[float]:
    """embed_text() with a Redis cache-aside layer keyed by the input text."""
    from services import cache

    key = _cache_key("emb", model, text)
    hit = await cache.cache_get(key)
    if hit is not None:
        try:
            return json.loads(hit)
        except (ValueError, TypeError):
            pass  # corrupted entry — fall through and regenerate

    embedding = await embed_text(text, model)
    await cache.cache_set(key, json.dumps(embedding), ttl)
    return embedding
