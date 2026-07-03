"""
Google Gemini service client.
Uses the google-genai SDK (successor to the deprecated google-generativeai).

This module is the ONLY place that touches the SDK. Agents call the functions
below and never import the SDK directly, so swapping or adding a provider is a
change to this file alone.

Model constants:
  GEMINI_FLASH = "gemini-2.5-flash"   — all agents except Agent 3
  GEMINI_PRO   = "gemini-2.5-pro"     — Agent 3 (document analysis, clinical signal extraction)
"""

import hashlib
import json
import logging
import os
from typing import Callable, Optional, Union

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None

GEMINI_FLASH = "gemini-2.5-flash"
# Agent 3 (records/image analysis) model. Defaults to Pro, but Pro is not on the
# Gemini free tier (quota limit 0), so a free-tier key must override this to a
# Flash model via GEMINI_PRO_MODEL, e.g. GEMINI_PRO_MODEL=gemini-2.5-flash.
GEMINI_PRO = os.getenv("GEMINI_PRO_MODEL", "").strip() or "gemini-2.5-pro"
# Current-generation Gemini embedding model. It is asymmetric: documents and queries
# must be embedded with matching task types (RETRIEVAL_DOCUMENT vs RETRIEVAL_QUERY) for
# good retrieval. Defaults to 3072-dim but supports Matryoshka truncation — we request
# 768 to match the vector(768) columns (and stay under pgvector's 2000-dim HNSW index
# cap). This is the only embedding model served on the current API: the older
# embedding-001 / text-embedding-004 both return 404, so everything (RAG corpus AND the
# scheme_data seed/search) uses this one model at 768 dims for a single vector space.
GEMINI_EMBED = "models/gemini-embedding-001"
GEMINI_EMBED_DIMS = 768

_RETRY_DELAYS = [5, 15]  # seconds to wait on 429 before each retry

# TTLs for the cross-session LLM cache (see services/cache.py).
CACHE_TTL_GENERATE = 7 * 24 * 3600   # scheme/clinic results are stable for days
CACHE_TTL_EMBED = 30 * 24 * 3600     # text -> embedding never changes for the same text


def _is_rate_limit(exc: Exception) -> bool:
    """429 detection by exception attribute, not string matching."""
    if isinstance(exc, genai_errors.APIError):
        return exc.code == 429
    return getattr(exc, "code", None) == 429 or getattr(exc, "status_code", None) == 429


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set — add it to backend/.env")
        _client = genai.Client(api_key=key)
    return _client


def validate_key_on_startup() -> None:
    """Call once at startup to surface a missing API key immediately."""
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


# ── JSON helpers ─────────────────────────────────────────────────────────────

def parse_json(raw: str):
    """
    Parse model output as JSON. json_mode responses are clean JSON already;
    this stays tolerant of stray markdown fences as a belt-and-braces measure
    (and for values cached before json_mode existed). Raises on invalid input.
    """
    text = (raw or "").strip()
    if text.startswith("```"):
        for part in text.split("```"):
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith(("{", "[")):
                text = candidate
                break
    return json.loads(text)


# ── Generation ───────────────────────────────────────────────────────────────

async def _generate_with_retry(coro_factory) -> str:
    """Run an async generate call with automatic retry on 429 rate limits."""
    import asyncio

    last_exc: Exception = RuntimeError("unknown error")
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            logger.warning(
                "Gemini 429 rate limit — waiting %ds before retry %d/%d...",
                delay, attempt, len(_RETRY_DELAYS),
            )
            await asyncio.sleep(delay)
        try:
            response = await coro_factory()
            return (response.text or "").strip()
        except Exception as exc:
            last_exc = exc
            if not _is_rate_limit(exc):
                raise
    raise last_exc


def _gen_config(json_mode: bool, temperature: Optional[float]) -> Optional[genai_types.GenerateContentConfig]:
    if not json_mode and temperature is None:
        return None
    kwargs: dict = {}
    if json_mode:
        kwargs["response_mime_type"] = "application/json"
    if temperature is not None:
        kwargs["temperature"] = temperature
    return genai_types.GenerateContentConfig(**kwargs)


async def generate(
    prompt: str,
    model: str = GEMINI_FLASH,
    *,
    json_mode: bool = False,
    temperature: Optional[float] = None,
) -> str:
    client = _get_client()
    config = _gen_config(json_mode, temperature)
    return await _generate_with_retry(
        lambda: client.aio.models.generate_content(model=model, contents=prompt, config=config)
    )


async def generate_json(
    prompt: str,
    model: str = GEMINI_FLASH,
    *,
    temperature: float = 0.1,
) -> str:
    """Structured-output generation: the model is constrained to emit JSON.
    Returns the raw JSON string; parse with parse_json()."""
    return await generate(prompt, model, json_mode=True, temperature=temperature)


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


def _to_part(part: Union[str, dict]):
    """Convert our provider-neutral part format into an SDK part.

    Accepted: plain strings (prompt text) and {"mime_type": ..., "data": ...}
    where data is raw bytes (preferred) or a base64 string (legacy callers).
    """
    if isinstance(part, str):
        return part
    data = part["data"]
    if isinstance(data, str):
        import base64
        data = base64.b64decode(data)
    return genai_types.Part.from_bytes(data=data, mime_type=part["mime_type"])


async def generate_multimodal(
    parts: list,
    model: str = GEMINI_FLASH,
    *,
    json_mode: bool = False,
) -> str:
    """Send a multimodal prompt (text + inline file data) to Gemini."""
    client = _get_client()
    contents = [_to_part(p) for p in parts]
    config = _gen_config(json_mode, None)
    return await _generate_with_retry(
        lambda: client.aio.models.generate_content(model=model, contents=contents, config=config)
    )


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


async def generate_pro_multimodal(parts: list, *, json_mode: bool = False) -> str:
    """Document and image analysis using Gemini 2.5 Pro (Agent 3)."""
    return await generate_multimodal(parts, model=GEMINI_PRO, json_mode=json_mode)


async def generate_pro_multimodal_safe(parts: list, fallback: str) -> str:
    try:
        return await generate_pro_multimodal(parts)
    except Exception as exc:
        logger.warning("Gemini Pro multimodal failed: %s", exc)
        return fallback


# ── Embeddings ───────────────────────────────────────────────────────────────

async def embed_text(
    text: str,
    model: str = GEMINI_EMBED,
    task_type: Optional[str] = None,
    output_dimensionality: int = GEMINI_EMBED_DIMS,
) -> list[float]:
    """
    Generate an embedding for the given text (768-dim by default).

    `task_type` sets the asymmetric side for retrieval ("retrieval_document" /
    "retrieval_query"); left unset the embedding is symmetric, which is what the
    scheme_data seed and its query search both use so they share one vector space.
    """
    client = _get_client()
    config = genai_types.EmbedContentConfig(
        task_type=task_type.upper() if task_type else None,
        output_dimensionality=output_dimensionality,
    )
    result = await client.aio.models.embed_content(model=model, contents=text, config=config)
    return list(result.embeddings[0].values)


async def embed_document(text: str) -> list[float]:
    """Embed a corpus chunk for storage (asymmetric RETRIEVAL_DOCUMENT side)."""
    return await embed_text(
        text, model=GEMINI_EMBED, task_type="retrieval_document",
        output_dimensionality=GEMINI_EMBED_DIMS,
    )


async def embed_query(text: str) -> list[float]:
    """Embed a user query for search (asymmetric RETRIEVAL_QUERY side)."""
    return await embed_text(
        text, model=GEMINI_EMBED, task_type="retrieval_query",
        output_dimensionality=GEMINI_EMBED_DIMS,
    )


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
    json_mode: bool = False,
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

    result = await generate(prompt, model, json_mode=json_mode)
    if _passes(validate, result):
        await cache.cache_set(key, result, ttl)
    return result


async def embed_text_cached(
    text: str,
    *,
    model: str = GEMINI_EMBED,
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
