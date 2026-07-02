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
import base64
import json
from typing import Optional

from fastapi import UploadFile

from services.session_store import get_session, update_session
from services import gemini

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
    b64 = base64.b64encode(content).decode()

    prompt = f"""You are VERA, a warm and caring health AI companion.

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
- Write in {lang}.
- Do not use em dashes."""

    text = await gemini.generate_pro_multimodal_safe(
        parts=[{"mime_type": mime_type, "data": b64}, prompt],
        fallback=_FALLBACK_EXPLANATION["text"],
    )

    return {"text": text or _FALLBACK_EXPLANATION["text"], "language": language, "document_type": ""}


async def _extract_signals(content: bytes, mime_type: str) -> dict:
    b64 = base64.b64encode(content).decode()

    prompt = """You are a clinical data extraction system. Read this medical document carefully and extract structured clinical signals for a cancer risk assessment system.

Your task is to identify findings that are relevant to cancer risk — abnormalities, polyps, lesions, irregular tissue, elevated markers, or recommendations for urgent follow-up.

You MUST return ONLY a valid JSON object in exactly this format. No prose before or after. No markdown fences. No explanation. Just the JSON:
{
  "anomalies": ["specific finding 1", "specific finding 2"],
  "severity": "high",
  "confidence": 0.85,
  "specialist_signal": "Gastroenterologist",
  "urgency_flag": true
}

Field definitions — follow these exactly:
- "anomalies": array of strings. Each string is one specific clinical finding, quoted directly or paraphrased from the document. Be specific: "12mm tubulovillous adenoma, ascending colon" not "abnormality found". Empty array [] if document is normal.
- "severity": exactly one of "high", "medium", or "low". Use "high" if findings indicate elevated cancer risk or require urgent follow-up. Use "medium" if findings warrant monitoring. Use "low" if the document is normal or routine.
- "confidence": float 0.0 to 1.0. How confident you are in this extraction based on document clarity and specificity of findings.
- "specialist_signal": string with the exact specialist type most relevant to these findings (e.g. "Gastroenterologist", "Oncologist", "Pulmonologist", "Dermatologist"), or null if not indicated.
- "urgency_flag": true if the document recommends urgent follow-up, repeat procedure, or immediate specialist referral. Otherwise false.

If the document is normal with no concerning findings: anomalies=[], severity="low", urgency_flag=false.
Return only the JSON object."""

    try:
        raw = await gemini.generate_pro_multimodal(
            parts=[{"mime_type": mime_type, "data": b64}, prompt]
        )
        text = raw.strip()
        if text.startswith("```"):
            parts_list = text.split("```")
            text = parts_list[1] if len(parts_list) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
    except Exception:
        return _FALLBACK_SIGNALS

    if not isinstance(result, dict):
        return _FALLBACK_SIGNALS

    return {
        "anomalies": result.get("anomalies") or [],
        "severity": result.get("severity", "medium"),
        "confidence": float(result.get("confidence", 0.7)),
        "specialist_signal": result.get("specialist_signal"),
        "urgency_flag": bool(result.get("urgency_flag", False)),
    }


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
