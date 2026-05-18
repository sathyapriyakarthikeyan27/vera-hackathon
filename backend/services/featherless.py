"""
Featherless AI service client.
OpenAI-compatible REST API — async, logs errors, never raises.

Primary model: "unsloth/medgemma-1.5-4b-it" (set FEATHERLESS_MODEL in .env)
Used for all structured medical reasoning in VERA:
  - Risk assessment JSON (Agent 1)
  - Clinical signal extraction from documents (Agent 3)
  - Medical document explanation (Agent 3)

Falls back gracefully when key is missing or model is loading.
"""

import asyncio
import base64
import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

FEATHERLESS_BASE = "https://api.featherless.ai/v1"
DEFAULT_MODEL = os.getenv("FEATHERLESS_MODEL", "unsloth/medgemma-1.5-4b-it")

# Featherless free tier can be slow on first call while model loads.
# 90s covers the cold-start window.
DEFAULT_TIMEOUT = 90.0

# Retry delays (seconds) when Featherless reports model_pending_deploy.
_DEPLOY_RETRIES = [10, 20, 30]


def _api_key() -> Optional[str]:
    return os.getenv("FEATHERLESS_API_KEY", "").strip() or None


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


async def chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[str]:
    """
    Send a text prompt to Featherless.
    Returns None on any failure — caller must provide its own fallback.
    """
    key = _api_key()
    if not key:
        logger.warning("FEATHERLESS_API_KEY not set — skipping Featherless call.")
        return None

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }

    for attempt, delay in enumerate([0] + _DEPLOY_RETRIES):
        if delay:
            logger.info("Featherless model deploying — retrying in %ds (attempt %d)...", delay, attempt)
            await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{FEATHERLESS_BASE}/chat/completions",
                    headers=_headers(),
                    json=payload,
                    timeout=timeout,
                )
            if res.is_success:
                return res.json()["choices"][0]["message"]["content"].strip()
            body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
            code = body.get("error", {}).get("code", "")
            if code == "model_pending_deploy":
                logger.info("Featherless model still deploying (model=%s)...", model)
                continue
            logger.warning(
                "Featherless chat error (model=%s status=%s): %s",
                model, res.status_code, res.text[:500],
            )
            return None
        except Exception as exc:
            logger.warning("Featherless chat failed (model=%s): %s", model, exc)
            return None

    logger.warning("Featherless model did not become ready after %d retries (model=%s).", len(_DEPLOY_RETRIES), model)
    return None


async def chat_json(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[dict]:
    """
    Send a prompt expecting a JSON response.
    Strips markdown fences if present. Returns None on any failure.
    """
    raw = await chat(prompt, model=model, max_tokens=max_tokens, timeout=timeout)
    if raw is None:
        return None
    try:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as exc:
        logger.warning("Featherless JSON parse failed: %s — raw: %.200s", exc, raw)
        return None


async def chat_multimodal(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[str]:
    """
    Send an image + text prompt to Featherless using the OpenAI vision format.
    Falls back to text-only if the model does not support vision.
    Returns None on any failure.
    """
    key = _api_key()
    if not key:
        logger.warning("FEATHERLESS_API_KEY not set — skipping multimodal call.")
        return None

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{mime_type};base64,{b64}"

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{FEATHERLESS_BASE}/chat/completions",
                headers=_headers(),
                json={
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }],
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },
                timeout=timeout,
            )
            if not res.is_success:
                logger.warning(
                    "Featherless multimodal error (model=%s status=%s): %s — falling back to text-only",
                    model, res.status_code, res.text[:500],
                )
                return await chat(prompt, model=model, max_tokens=max_tokens, timeout=timeout)
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning(
            "Featherless multimodal failed (model=%s): %s — falling back to text-only",
            model, exc,
        )
        return await chat(prompt, model=model, max_tokens=max_tokens, timeout=timeout)


async def chat_multimodal_json(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[dict]:
    """Multimodal call expecting a JSON response. Returns None on any failure."""
    raw = await chat_multimodal(
        image_bytes, mime_type, prompt,
        model=model, max_tokens=max_tokens, timeout=timeout,
    )
    if raw is None:
        return None
    try:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as exc:
        logger.warning("Featherless multimodal JSON parse failed: %s — raw: %.200s", exc, raw)
        return None
