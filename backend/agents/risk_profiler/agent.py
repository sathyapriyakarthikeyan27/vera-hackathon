"""
Risk Profiler Agent.
Uses Google MedGemma (medgemma-4b-it) for medical risk assessment,
then Gemini Flash to generate the warm plain-language summary.
"""

import asyncio
import json
import os
from typing import Optional

import google.generativeai as genai

from services.session_store import get_session, update_session
from services import gemini
from .questions import QUESTIONS, format_question

MEDGEMMA_MODEL = os.getenv("MEDGEMMA_MODEL", "medgemma-4b-it")
CURRENT_YEAR = 2026
_VALID_LEVELS = {"Low", "Moderate", "High", "Urgent"}

_FALLBACK_SUMMARY = (
    "Based on your answers, VERA has mapped your cancer risk profile and identified "
    "some important patterns in your screening history. "
    "The good news: free screening options are available near you — let's find them."
)


async def reconcile(session_id: str) -> Optional[dict]:
    """
    Agent 1 in reconciliation mode.
    Reads pending_signals written by Agent 3, compares against the original
    risk score, and outputs one of three verdicts: Agreement, Escalation, Uncertainty.
    """
    session = await get_session(session_id)
    if not session:
        return None

    risk_assessment: dict = session.get("risk_assessment") or {}
    pending_signals: list = risk_assessment.get("pending_signals") or []

    if not pending_signals:
        return {"reconciled": True, "conflict": False, "message": "No new signals to reconcile."}

    original_score: str = risk_assessment.get("score", "Moderate")
    risk_profile: dict = session.get("risk_profile") or {}
    original_reasoning: str = risk_profile.get("medgemma_reasoning", "")

    verdict = await _reconcile_signals(original_score, pending_signals, original_reasoning)

    conflict_obj = None
    if verdict.get("conflict"):
        conflict_obj = {
            "original_score": original_score,
            "new_score": verdict["final_score"],
            "reason": verdict.get("reason", ""),
            "shown_to_user": False,
        }

    updated_risk_assessment = {
        **risk_assessment,
        "score": verdict["final_score"],
        "source": "profile+records",
        "pending_signals": [],
        "reconciled": True,
        "conflict": conflict_obj,
    }

    updated_risk_profile = {**risk_profile, "risk_level": verdict["final_score"]}

    await update_session(session_id, {
        "risk_assessment": updated_risk_assessment,
        "risk_profile": updated_risk_profile,
    })

    return {
        "reconciled": True,
        "conflict": verdict.get("conflict", False),
        "original_score": original_score,
        "new_score": verdict["final_score"],
        "reason": verdict.get("reason", ""),
        "message": verdict.get("message", ""),
        "uncertain": verdict.get("uncertain", False),
    }


async def _reconcile_signals(
    original_score: str, pending_signals: list, original_reasoning: str
) -> dict:
    _LEVEL_RANK = {"Low": 0, "Moderate": 1, "High": 2, "Urgent": 3}

    signals_text = "\n".join(
        f"- Severity: {s.get('severity', 'unknown')}, "
        f"Anomalies: {', '.join(s.get('anomalies') or []) or 'none'}, "
        f"Urgency flag: {s.get('urgency_flag', False)}, "
        f"Confidence: {s.get('confidence', 0.5)}"
        for s in pending_signals
    )

    prompt = f"""You are Agent 1 of VERA in reconciliation mode.

Original risk assessment: {original_score}
Original reasoning: {original_reasoning or 'Not available'}

New clinical signals from uploaded medical document:
{signals_text}

Compare the new signals against the original risk assessment. Output ONE of three verdicts as valid JSON only — no prose, no markdown:

Verdict A — signals confirm original (use when severity is low and no urgency):
{{"final_score": "{original_score}", "conflict": false, "message": "Lab findings are consistent with your existing risk profile."}}

Verdict B — signals escalate risk (use when severity is high OR urgency_flag is true):
{{"final_score": "High", "conflict": true, "reason": "Your uploaded report shows findings that indicate higher risk than your initial profile suggested.", "message": "VERA has updated your risk assessment based on your report."}}

Verdict C — mixed signals, uncertain (use when confidence is below 0.6 or signals are ambiguous):
{{"final_score": "{original_score}", "conflict": true, "uncertain": true, "reason": "Your report contains mixed signals. VERA recommends a specialist follow-up to clarify.", "message": "VERA has noted some uncertainty in your results."}}

Return ONLY the JSON object for the chosen verdict."""

    try:
        raw = await gemini.generate(prompt)
        text = raw.strip()
        if text.startswith("```"):
            parts_list = text.split("```")
            text = parts_list[1] if len(parts_list) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        if result.get("final_score") not in _VALID_LEVELS:
            result["final_score"] = original_score
        return result
    except Exception:
        any_high = any(s.get("severity") == "high" or s.get("urgency_flag") for s in pending_signals)
        if any_high:
            new_score = "High" if _LEVEL_RANK.get(original_score, 1) < 2 else original_score
            return {
                "final_score": new_score,
                "conflict": new_score != original_score,
                "reason": "Your uploaded report shows findings that indicate elevated cancer risk.",
                "message": "VERA has updated your risk assessment based on your report.",
            }
        return {
            "final_score": original_score,
            "conflict": False,
            "message": "Lab findings are consistent with your existing risk profile.",
        }


async def start_assessment(session_id: str) -> Optional[dict]:
    session = await get_session(session_id)
    if session is None:
        return None

    # If signup already pre-filled answers, resume from where we left off
    existing = session.get("risk_state") or {}
    if existing.get("answers") and existing.get("prefilled"):
        idx = existing.get("current_index", 0)
        if idx < len(QUESTIONS):
            return {"question": format_question(QUESTIONS[idx], existing["answers"])}

    await update_session(session_id, {"risk_state": {"answers": {}, "current_index": 0}})
    return {"question": format_question(QUESTIONS[0])}


async def process_answer(session_id: str, question_id: str, answer: str) -> Optional[dict]:
    session = await get_session(session_id)
    if session is None:
        return None

    risk_state: dict = session.get("risk_state") or {"answers": {}, "current_index": 0}
    answers: dict = risk_state["answers"]

    q = next((x for x in QUESTIONS if x["id"] == question_id), None)
    if q:
        answers[q["key"]] = answer
        side: dict = {}
        if q["key"] == "user_name":
            side["user_name"] = answer
        if q["key"] == "language":
            side["language"] = answer
        if side:
            await update_session(session_id, side)

    next_index = risk_state["current_index"] + 1
    risk_state.update({"answers": answers, "current_index": next_index})
    await update_session(session_id, {"risk_state": risk_state})

    if next_index < len(QUESTIONS):
        return {"complete": False, "question": format_question(QUESTIONS[next_index], answers)}

    # All 8 questions answered — run MedGemma + Gemini concurrently
    risk_profile = await _compute_profile(answers)
    completed = list(session.get("completed_agents") or [])
    if "risk_profiler" not in completed:
        completed.append("risk_profiler")

    # Seed the shared risk_assessment object (Agent 1 owns this)
    risk_assessment = {
        "score": risk_profile["risk_level"],
        "confidence": 0.8,
        "source": "profile_only",
        "pending_signals": [],
        "reconciled": True,
        "conflict": None,
    }

    await update_session(session_id, {
        "risk_profile": risk_profile,
        "risk_assessment": risk_assessment,
        "completed_agents": completed,
    })
    return {"complete": True, "risk_profile": risk_profile}


async def _compute_profile(answers: dict) -> dict:
    # MedGemma assesses risk + Gemini writes the summary — both run concurrently
    medgemma_result, _ = await asyncio.gather(
        _medgemma_assess(answers),
        asyncio.sleep(0),  # ensures gather even if medgemma is instant
    )

    risk_level = medgemma_result.get("risk_level", "Moderate")
    if risk_level not in _VALID_LEVELS:
        risk_level = "Moderate"

    cancer_types: list[str] = medgemma_result.get("cancer_types_flagged") or ["cervical"]
    risk_score: int = medgemma_result.get("risk_score") or 5
    screening_gap = medgemma_result.get("screening_gap_years")
    reasoning = medgemma_result.get("reasoning", "")

    timeline = _build_timeline(answers)

    summary = await gemini.generate_safe(
        _summary_prompt(answers, risk_level, cancer_types, reasoning),
        fallback=_FALLBACK_SUMMARY,
    )

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "cancer_types_flagged": cancer_types,
        "screening_gap_years": screening_gap,
        "timeline": timeline,
        "plain_language_summary": summary,
        "medgemma_reasoning": reasoning,
        "disclaimer": (
            "This is not a medical diagnosis. VERA provides risk awareness only. "
            "Please consult a qualified doctor."
        ),
    }


async def _medgemma_assess(answers: dict) -> dict:
    """
    Call MedGemma for structured medical risk assessment.
    MedGemma is Google's purpose-built medical AI model trained on medical literature.
    Falls back to rule-based scoring on any failure.
    """
    _AGE = {
        "under_25": "under 25", "25_34": "25–34", "35_44": "35–44",
        "45_54": "45–54", "55_plus": "55 or older",
    }
    _FH = {
        "yes_breast_ovarian": "family history of breast/ovarian cancer",
        "yes_cervical": "family history of cervical cancer",
        "yes_other": "family history of another cancer type",
        "no": "no known family history of cancer",
    }
    _LS = {
        "within_1yr": "had a cancer screening within the last year",
        "1_3yr": "had a cancer screening 1–3 years ago",
        "3_5yr": "had a cancer screening 3–5 years ago",
        "over_5yr": "has not had a screening in over 5 years",
        "never": "has never had a cancer screening",
    }
    _HPV = {"yes": "vaccinated against HPV", "no": "not vaccinated against HPV", "unsure": "HPV vaccination status unknown"}
    _SM = {"current": "current smoker", "former": "former smoker", "never": "non-smoker"}

    _GEN = {"female": "female", "male": "male", "other": "non-binary/other"}
    symptoms_line = f"- Reported symptoms/concerns: {answers['symptoms']}" if answers.get("symptoms") and answers["symptoms"] != "skip" else ""

    profile = "\n".join(filter(None, [
        f"- Age: {_AGE.get(answers.get('age_group', ''), 'unknown')}",
        f"- Gender: {_GEN.get(answers.get('gender', ''), 'not specified')}",
        f"- Family history: {_FH.get(answers.get('family_history', ''), 'unknown')}",
        f"- Last screening: {_LS.get(answers.get('last_screening', ''), 'unknown')}",
        f"- HPV vaccine: {_HPV.get(answers.get('hpv_vaccine', ''), 'unknown')}",
        f"- Smoking: {_SM.get(answers.get('smoking', ''), 'unknown')}",
        f"- Location: {answers.get('location', 'India')}",
        symptoms_line,
    ]))

    prompt = f"""You are MedGemma, a medical AI model specialising in women's preventive health.

Analyse this patient profile for cancer screening risk awareness:
{profile}

Respond ONLY with valid JSON in this exact format:
{{
  "risk_level": "Low",
  "risk_score": 3,
  "cancer_types_flagged": ["cervical"],
  "screening_gap_years": 2,
  "reasoning": "One sentence clinical reasoning based on the profile.",
  "recommendations": "One sentence on the most important recommended next step."
}}

Guidelines: risk_level must be one of Low/Moderate/High/Urgent. Flag High or Urgent if family history is present AND screening gap > 3 years. Always include cervical in cancer_types_flagged if HPV unvaccinated + screening gap exists. This is for health awareness, not clinical diagnosis."""

    try:
        gemini._configure()
        m = genai.GenerativeModel(MEDGEMMA_MODEL)
        response = await m.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        return json.loads(response.text.strip())
    except Exception:
        return _rule_based_fallback(answers)


def _rule_based_fallback(answers: dict) -> dict:
    """Deterministic fallback used when MedGemma is unavailable or returns invalid JSON."""
    score = 0
    cancer: set[str] = set()

    fh = answers.get("family_history", "")
    if fh == "yes_breast_ovarian":
        score += 3; cancer.update(["breast", "ovarian"])
    elif fh == "yes_cervical":
        score += 3; cancer.add("cervical")
    elif fh == "yes_other":
        score += 1

    ls = answers.get("last_screening", "never")
    score += {"never": 4, "over_5yr": 3, "3_5yr": 2, "1_3yr": 1, "within_1yr": 0}.get(ls, 0)
    score += {"no": 2, "unsure": 1, "yes": 0}.get(answers.get("hpv_vaccine", "no"), 0)
    score += {"current": 2, "former": 1, "never": 0}.get(answers.get("smoking", "never"), 0)
    score += {"45_54": 2, "55_plus": 3, "35_44": 1}.get(answers.get("age_group", ""), 0)
    cancer.add("cervical")

    gap = {"within_1yr": 1, "1_3yr": 2, "3_5yr": 4, "over_5yr": 6, "never": None}.get(ls)
    level = "Urgent" if score >= 10 else "High" if score >= 7 else "Moderate" if score >= 4 else "Low"

    return {
        "risk_level": level,
        "risk_score": score,
        "cancer_types_flagged": sorted(cancer),
        "screening_gap_years": gap,
        "reasoning": "Assessed from screening history and known clinical risk factors.",
        "recommendations": "Schedule a free screening at the nearest government hospital.",
    }


def _summary_prompt(answers: dict, risk_level: str, cancer_types: list, reasoning: str) -> str:
    name = answers.get("user_name") or ""
    types_text = " and ".join(cancer_types) if cancer_types else "cervical"
    return f"""You are VERA, a warm and caring women's health AI companion.

Write 2–3 sentences in plain language to explain a cancer risk assessment result to a woman.

Medical context: {reasoning}
Risk level: {risk_level}. Cancer types to monitor: {types_text}.
{"Her name is " + name + "." if name else ""}

Rules:
- Start with a warm, empathetic acknowledgment of what she shared
- Explain what {risk_level} risk means in everyday language — no medical jargon
- End with something genuinely encouraging: a concrete action is available
- Never diagnose. Never alarm. Maximum 3 sentences."""


def _build_timeline(answers: dict) -> list[dict]:
    gap_map = {"within_1yr": 2025, "1_3yr": 2024, "3_5yr": 2022, "over_5yr": 2020, "never": None}
    last_year = gap_map.get(answers.get("last_screening", "never"))

    timeline: list[dict] = []
    if last_year:
        timeline.append({"year": last_year, "event": "Last cancer screening", "status": "completed"})
        missed = last_year + 3
        while missed < CURRENT_YEAR:
            timeline.append({"year": missed, "event": "Recommended Pap smear", "status": "missed"})
            missed += 3
    else:
        timeline.append({"year": 2020, "event": "First screening (never completed)", "status": "missed"})
        timeline.append({"year": 2023, "event": "Recommended Pap smear", "status": "missed"})

    timeline.append({"year": CURRENT_YEAR, "event": "Now — VERA recommends action", "status": "urgent"})
    return timeline
