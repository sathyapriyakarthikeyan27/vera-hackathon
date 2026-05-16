"""
Featherless AI service client.
OpenAI-compatible REST API — async, never raises (degrades gracefully).

Model: medalpaca/medalpaca-7b (Apache 2.0 licensed)
Override via FEATHERLESS_MODEL env var if needed.
"""

import os
from typing import Optional

import httpx

FEATHERLESS_BASE = "https://api.featherless.ai/v1"
# Apache 2.0 licensed medical domain model — verify availability at featherless.ai
DEFAULT_MODEL = os.getenv("FEATHERLESS_MODEL", "medalpaca/medalpaca-7b")


async def chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 200,
    timeout: float = 20.0,
) -> Optional[str]:
    """
    Send a prompt to Featherless AI.
    Returns None on any failure — ensures demo never crashes due to this call.
    """
    api_key = os.getenv("FEATHERLESS_API_KEY")
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{FEATHERLESS_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },
                timeout=timeout,
            )
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
