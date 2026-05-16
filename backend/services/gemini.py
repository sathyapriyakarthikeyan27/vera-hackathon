"""
Google Gemini service client.
Uses google-generativeai SDK (google-generativeai==0.8.3).
"""

import os
import google.generativeai as genai

_configured = False


def _configure() -> None:
    global _configured
    if not _configured and os.getenv("GEMINI_API_KEY"):
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        _configured = True


async def generate(prompt: str, model: str = "gemini-2.0-flash") -> str:
    _configure()
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set")
    m = genai.GenerativeModel(model)
    response = await m.generate_content_async(prompt)
    return response.text.strip()


async def generate_safe(
    prompt: str,
    fallback: str,
    model: str = "gemini-2.0-flash",
) -> str:
    """Like generate() but returns fallback text on any error — never raises."""
    try:
        return await generate(prompt, model)
    except Exception:
        return fallback


async def generate_multimodal(
    parts: list,
    model: str = "gemini-2.0-flash",
) -> str:
    """Send a multimodal prompt (text + inline file data) to Gemini."""
    _configure()
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set")
    m = genai.GenerativeModel(model)
    response = await m.generate_content_async(parts)
    return response.text.strip()


async def generate_multimodal_safe(
    parts: list,
    fallback: str,
    model: str = "gemini-2.0-flash",
) -> str:
    try:
        return await generate_multimodal(parts, model)
    except Exception:
        return fallback


async def embed_text(text: str, model: str = "models/text-embedding-004") -> list[float]:
    """Generate a 768-dimensional embedding for the given text."""
    import asyncio
    _configure()
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set")
    result = await asyncio.to_thread(genai.embed_content, model=model, content=text)
    return result["embedding"]
