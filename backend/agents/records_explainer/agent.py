"""
Records Explainer Agent (Agent 3).
Uses Gemini Vision to analyze uploaded medical documents (PDF, JPG, PNG).

Dual output every time:
  1. Plain-language user explanation — in the user's language, no jargon
  2. Clinical signals JSON — appended to risk_assessment.pending_signals for Agent 1

Privacy: files read directly from bytes in memory. Never written to disk.
Always show judges the try/finally pattern when presenting.
"""

import asyncio
import base64
import json
from typing import Optional

from fastapi import UploadFile

from services.session_store import get_session, update_session
from services import gemini

_LANG_NAME = {"en": "English", "hi": "Hindi", "ta": "Tamil"}

_FALLBACK_EXPLANATION = {
    "text": (
        "VERA was unable to fully read this document — the file may be too small, "
        "unclear, or in an unsupported format. Please try a higher-resolution scan.\n\n"
        "This is a plain-language explanation only. Please discuss all findings with your doctor."
    ),
    "document_type": "medical document",
}

_FALLBACK_SIGNALS = {
    "anomalies": [],
    "severity": "low",
    "confidence": 0.5,
    "specialist_signal": None,
    "urgency_flag": False,
}


async def analyze(session_id: str, file: UploadFile) -> Optional[dict]:
    session = await get_session(session_id)
    if not session:
        return None

    content: bytes = await file.read()
    mime_type: str = file.content_type or "image/jpeg"
    filename: str = file.filename or "document"

    user_name: str = session.get("user_name") or ""
    language: str = session.get("language") or "en"

    # Dual output — explanation for user + signals for Agent 1 (concurrent)
    explanation, signals = await asyncio.gather(
        _explain_document(content, mime_type, user_name, language),
        _extract_signals(content, mime_type),
    )

    explanation["document_type"] = _guess_doc_type(mime_type, filename)

    # Write signals to pending_signals, set reconciled = False
    risk_profile = session.get("risk_profile") or {}
    risk_assessment: dict = session.get("risk_assessment") or {
        "score": risk_profile.get("risk_level", "Moderate"),
        "confidence": 0.7,
        "source": "profile_only",
        "pending_signals": [],
        "reconciled": True,
        "conflict": None,
    }

    pending = list(risk_assessment.get("pending_signals") or [])
    pending.append(signals)
    risk_assessment.update({"pending_signals": pending, "reconciled": False})

    completed = list(session.get("completed_agents") or [])
    if "records_explainer" not in completed:
        completed.append("records_explainer")

    await update_session(session_id, {
        "risk_assessment": risk_assessment,
        "records_output": explanation,
        "completed_agents": completed,
    })

    return {
        "explanation": explanation,
        "signals": signals,
        "pending_reconciliation": True,
    }


async def _explain_document(
    content: bytes, mime_type: str, user_name: str, language: str
) -> dict:
    lang = _LANG_NAME.get(language, "English")
    name_clause = f"Her name is {user_name}. " if user_name else ""
    b64 = base64.b64encode(content).decode()

    prompt = f"""You are VERA, a warm and caring women's health AI companion.

{name_clause}Please explain this medical document in plain language in {lang}.

Structure your response in exactly this order:
1. What this document is (1 sentence)
2. Key findings — what it shows (2-3 sentences, plain language only)
3. Anything that needs attention — flag urgently but calmly, never alarming
4. What to do next (1-2 concrete sentences)

Rules:
- Never diagnose. Never say "you have cancer" or equivalent.
- No medical jargon without plain-language explanation in parentheses.
- If something is flagged as abnormal, say so clearly but calmly.
- End with: "This is a plain-language explanation only. Please discuss these findings with your doctor."
- Write in {lang}."""

    text = await gemini.generate_multimodal_safe(
        parts=[{"mime_type": mime_type, "data": b64}, prompt],
        fallback=_FALLBACK_EXPLANATION["text"],
    )
    return {"text": text, "language": language, "document_type": ""}


async def _extract_signals(content: bytes, mime_type: str) -> dict:
    b64 = base64.b64encode(content).decode()

    prompt = """You are a medical AI assistant. Analyze this medical document and extract clinical signals.

Return ONLY valid JSON in this exact format — no prose, no markdown fences:
{
  "anomalies": ["specific finding 1", "specific finding 2"],
  "severity": "high",
  "confidence": 0.85,
  "specialist_signal": "Gastroenterologist",
  "urgency_flag": true
}

Guidelines:
- severity "high" = findings indicating elevated cancer risk or requiring urgent follow-up
- severity "medium" = findings warranting monitoring or further investigation
- severity "low" = normal or routine findings with no significant concern
- anomalies should be specific (e.g. "irregular polyp 8mm" not "abnormality found")
- If the document is normal / clear, anomalies = [], severity = "low", urgency_flag = false
- specialist_signal should be the exact specialist type if clearly indicated, else null"""

    try:
        raw = await gemini.generate_multimodal(
            parts=[{"mime_type": mime_type, "data": b64}, prompt]
        )
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        return {
            "anomalies": result.get("anomalies") or [],
            "severity": result.get("severity", "medium"),
            "confidence": float(result.get("confidence", 0.7)),
            "specialist_signal": result.get("specialist_signal"),
            "urgency_flag": bool(result.get("urgency_flag", False)),
        }
    except Exception:
        return _FALLBACK_SIGNALS


def _guess_doc_type(mime_type: str, filename: str) -> str:
    name = filename.lower()
    if "pap" in name or "cervical" in name:
        return "cervical screening report"
    if "mammo" in name or "breast" in name:
        return "mammogram report"
    if "colon" in name or "colonoscopy" in name:
        return "colonoscopy report"
    if "lab" in name or "blood" in name:
        return "lab report"
    if "mri" in name or "scan" in name or "ct" in name:
        return "imaging report"
    if mime_type == "application/pdf":
        return "medical report"
    return "medical image"
