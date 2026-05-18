"""
Google Gemini service client.
Uses google-generativeai SDK (google-generativeai==0.8.3).

MedGemma (medgemma-4b-it / medgemma-27b-it) requires Vertex AI or special
allowlist access — it is NOT available via the standard Gemini API key.
MEDGEMMA_MODEL defaults to gemini-2.5-flash-lite so all calls work out of the box.
Set MEDGEMMA_MODEL=medgemma-4b-it in .env only if you have Vertex AI access.
"""

import asyncio
import logging
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

_configured = False

# Model used for medical reasoning. Defaults to Gemini Flash because
# MedGemma requires Vertex AI access not available on the standard API key.
MEDGEMMA_MODEL = os.getenv("MEDGEMMA_MODEL", "gemini-2.5-flash-lite")

_RETRY_DELAYS = [5, 15]  # seconds to wait on 429 before each retry


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
        logger.info("Gemini API configured (model default: gemini-2.5-flash-lite, medical model: %s).", MEDGEMMA_MODEL)


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
            "STARTUP: GEMINI_API_KEY is present (length=%d). Medical model: %s.",
            len(key), MEDGEMMA_MODEL,
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


async def generate(prompt: str, model: str = "gemini-2.5-flash-lite") -> str:
    _configure()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is not set — add it to backend/.env")
    m = genai.GenerativeModel(model)
    return await _generate_with_retry(m, prompt)


async def generate_safe(
    prompt: str,
    fallback: str,
    model: str = "gemini-2.5-flash-lite",
) -> str:
    """Like generate() but returns fallback text on any error — never raises."""
    try:
        return await generate(prompt, model)
    except Exception as exc:
        logger.warning("Gemini generate_safe failed (model=%s): %s", model, exc)
        return fallback


async def generate_multimodal(parts: list, model: str = "gemini-2.5-flash-lite") -> str:
    """Send a multimodal prompt (text + inline file data) to Gemini."""
    _configure()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is not set")
    m = genai.GenerativeModel(model)
    return await _generate_with_retry(m, parts)


async def generate_multimodal_safe(
    parts: list,
    fallback: str,
    model: str = "gemini-2.5-flash-lite",
) -> str:
    try:
        return await generate_multimodal(parts, model)
    except Exception as exc:
        logger.warning("Gemini generate_multimodal_safe failed (model=%s): %s", model, exc)
        return fallback


async def generate_medgemma_multimodal(parts: list) -> str:
    """
    Medical document / image analysis.
    Uses MEDGEMMA_MODEL (defaults to gemini-2.5-flash-lite).
    Set MEDGEMMA_MODEL=medgemma-4b-it only if you have Vertex AI access.
    """
    _configure()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is not set")
    m = genai.GenerativeModel(MEDGEMMA_MODEL)
    return await _generate_with_retry(m, parts)


async def generate_medgemma_multimodal_safe(parts: list, fallback: str) -> str:
    try:
        return await generate_medgemma_multimodal(parts)
    except Exception as exc:
        logger.warning("Medical model call failed (model=%s): %s", MEDGEMMA_MODEL, exc)
        return fallback


async def embed_text(text: str, model: str = "models/text-embedding-004") -> list[float]:
    """Generate a 768-dimensional embedding for the given text."""
    _configure()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is not set")
    result = await asyncio.to_thread(genai.embed_content, model=model, content=text)
    return result["embedding"]
