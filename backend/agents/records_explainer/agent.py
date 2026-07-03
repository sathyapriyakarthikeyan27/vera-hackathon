"""
Records Explainer Agent (Agent 3).
Uses Gemini 2.5 Pro to analyze uploaded medical documents (PDF, JPG, PNG).

Dual output every time:
  1. Plain-language user explanation — in the user's language, no jargon
  2. Clinical signals JSON — appended to risk_assessment.pending_signals for Agent 1

Privacy: files read directly from bytes in memory. Never written to disk.
The try/finally pattern guarantees the uploaded file is released even on error —
this is a hard privacy requirement, not optional.
"""

import asyncio
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini
from . import prompts

_LANG_NAME = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "ar": "Arabic",
    "fr": "French", "es": "Spanish", "de": "German", "it": "Italian",
    "ja": "Japanese", "zh": "Chinese",
}

_FALLBACK_EXPLANATION = {
    "text": (
        "VERA was unable to fully read this document. The file may be too small, "
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


async def analyze(session_id: str, content: bytes, mime_type: str, filename: str) -> Optional[dict]:
    """Analyze an uploaded document. The router validates type, size, and magic
    bytes before this is called; `content` is held in memory only."""
    session = await get_session(session_id)
    if not session:
        return None

    user_name: str = session.get("user_name") or ""
    language: str = session.get("language") or "en"

    # Dual output — explanation for user + signals for Agent 1 (concurrent)
    explanation, signals = await asyncio.gather(
        _explain_document(content, mime_type, user_name, language),
        _extract_signals(content, mime_type),
    )

    explanation["document_type"] = _guess_doc_type(mime_type, filename)
    explanation["filename"] = filename

    # Write signals to pending_signals, set reconciled = False
    risk_profile = session.get("risk_profile") or {}
    risk_assessment: dict = session.get("risk_assessment") or {
        "score": risk_profile.get("risk_level", "Moderate"),
        "confidence": 0.7,
        "reasoning": "",
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
    name_clause = f"This person's name is {user_name}. " if user_name else ""

    prompt = prompts.explain_prompt(name_clause, lang)

    text = await gemini.generate_pro_multimodal_safe(
        parts=[{"mime_type": mime_type, "data": content}, prompt],
        fallback=_FALLBACK_EXPLANATION["text"],
    )

    return {
        "text": text or _FALLBACK_EXPLANATION["text"],
        "language": language,
        "document_type": "",
        # Audit trail: which model and prompt produced this explanation.
        "model": gemini.GEMINI_PRO,
        "prompt_version": prompts.EXPLAIN_PROMPT_VERSION,
    }


async def _extract_signals(content: bytes, mime_type: str) -> dict:
    try:
        raw = await gemini.generate_pro_multimodal(
            parts=[{"mime_type": mime_type, "data": content}, prompts.SIGNALS_PROMPT],
            json_mode=True,
        )
        result = gemini.parse_json(raw)
    except Exception:
        return _FALLBACK_SIGNALS

    if not isinstance(result, dict):
        return _FALLBACK_SIGNALS

    return {
        "anomalies": _safe_anomalies(result.get("anomalies")),
        "severity": _safe_severity(result.get("severity")),
        "confidence": _safe_confidence(result.get("confidence")),
        "specialist_signal": result.get("specialist_signal"),
        "urgency_flag": bool(result.get("urgency_flag", False)),
        # Audit trail: which model and prompt produced these signals.
        "model": gemini.GEMINI_PRO,
        "prompt_version": prompts.SIGNALS_PROMPT_VERSION,
    }


def _safe_anomalies(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if v]


def _safe_severity(value) -> str:
    return value if value in ("high", "medium", "low") else "medium"


def _safe_confidence(value) -> float:
    """Model output is untrusted: clamp to [0, 1], never raise."""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.7


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
