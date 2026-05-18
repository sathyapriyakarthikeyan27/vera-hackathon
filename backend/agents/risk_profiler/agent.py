"""
Risk Profiler Agent.
Uses MedGemma for structured medical risk assessment,
then Gemini Flash for a personalized plain-language summary.
"""

import asyncio
import json
import logging
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini
from .questions import QUESTIONS, format_question

logger = logging.getLogger(__name__)

CURRENT_YEAR = 2026
_VALID_LEVELS = {"Low", "Moderate", "High", "Urgent"}

_FALLBACK_SUMMARY = (
    "Based on your answers, I've mapped your cancer risk profile and found some important "
    "patterns in your screening history. "
    "The good news: free screening options are available near you. Let me find them for you."
)

MAX_ASSESSMENT_QUESTIONS = 6

_AGE_LABELS = {
    "under_25": "under 25", "25_34": "25 to 34", "35_44": "35 to 44",
    "45_54": "45 to 54", "55_plus": "over 55",
}
_FH_LABELS = {
    "yes_breast_ovarian": "family history of breast and ovarian cancer",
    "yes_cervical": "family history of cervical cancer",
    "yes_colorectal": "family history of colorectal cancer",
    "yes_other": "family history of another cancer type",
    "no": "no known family history of cancer",
}
_SMOKING_LABELS = {
    "current": "current smoker",
    "former": "former smoker",
    "never": "non-smoker",
}


def _build_profile_context(answers: dict) -> str:
    """Build a concise profile summary used across multiple prompts."""
    parts = []
    if age := _AGE_LABELS.get(answers.get("age_group", "")):
        parts.append(f"Age: {age}")
    if gender := answers.get("gender"):
        parts.append(f"Gender: {gender}")
    if fh := _FH_LABELS.get(answers.get("family_history", "")):
        parts.append(f"Family history: {fh}")
    if sm := _SMOKING_LABELS.get(answers.get("smoking", "")):
        parts.append(f"Smoking: {sm}")
    if loc := answers.get("location"):
        parts.append(f"Location: {loc}")
    if answers.get("symptoms") and answers["symptoms"] != "skip":
        parts.append(f"Reported concern: {answers['symptoms']}")
    return "\n".join(f"- {p}" for p in parts)


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

    risk_state: dict = session.get("risk_state") or {}
    answers: dict = risk_state.get("answers") or {}

    verdict = await _reconcile_signals(original_score, pending_signals, original_reasoning, answers)

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
    original_score: str, pending_signals: list, original_reasoning: str, answers: dict
) -> dict:
    _LEVEL_RANK = {"Low": 0, "Moderate": 1, "High": 2, "Urgent": 3}

    signals_text = "\n".join(
        f"- Severity: {s.get('severity', 'unknown')}, "
        f"Findings: {', '.join(s.get('anomalies') or []) or 'none'}, "
        f"Urgency: {s.get('urgency_flag', False)}, "
        f"Confidence: {s.get('confidence', 0.5)}"
        for s in pending_signals
    )

    profile_context = _build_profile_context(answers)
    cancer_types = ", ".join(
        (answers.get("risk_profile") or {}).get("cancer_types_flagged") or []
    ) or "not specified"

    prompt = f"""Compare a person's original cancer risk profile against new clinical signals from an uploaded medical document. Decide whether the new findings change the risk level.

Person profile:
{profile_context}

Original risk level: {original_score}
Original clinical reasoning: {original_reasoning or 'Not available'}

New clinical signals from uploaded document:
{signals_text}

Consider this person's specific risk factors (age, gender, family history, smoking history) when evaluating whether the new signals are clinically significant for them. A high-severity finding in someone with a family history of that cancer type should carry more weight than in someone with no such history.

Output ONE of three verdicts as valid JSON only — no prose, no markdown:

Verdict A — signals confirm original (use when severity is low and no urgency):
{{"final_score": "{original_score}", "conflict": false, "message": "Your report findings are consistent with your existing risk profile."}}

Verdict B — signals escalate risk (use when severity is high OR urgency_flag is true AND consistent with this person's risk profile):
{{"final_score": "High", "conflict": true, "reason": "Your uploaded report contains findings that suggest a higher risk level than your initial profile indicated. Given your family history and screening gap, this needs prompt attention.", "message": "I've updated your risk assessment based on your report."}}

Verdict C — mixed or uncertain signals (use when confidence is below 0.6 or signals are ambiguous given this person's profile):
{{"final_score": "{original_score}", "conflict": true, "uncertain": true, "reason": "Your report contains some findings that need a specialist to review. I can not be certain whether they change your overall risk level.", "message": "I have noted some findings in your report that warrant a specialist follow-up."}}

Return ONLY the JSON object."""

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
                "message": "I've updated your risk assessment based on your report.",
            }
        return {
            "final_score": original_score,
            "conflict": False,
            "message": "Your report findings are consistent with your existing risk profile.",
        }


async def start_assessment(session_id: str) -> Optional[dict]:
    session = await get_session(session_id)
    if session is None:
        return None

    risk_state = session.get("risk_state") or {}
    answers = risk_state.get("answers") or {}

    new_state = {**risk_state, "answers": answers, "current_index": 1, "question_keys": {}}
    await update_session(session_id, {"risk_state": new_state})

    question = await generate_next_question(answers, 1)
    return {"question": question, "total": MAX_ASSESSMENT_QUESTIONS}


async def process_answer(session_id: str, question_id: str, answer: str, key: Optional[str] = None) -> Optional[dict]:
    session = await get_session(session_id)
    if session is None:
        return None

    risk_state = session.get("risk_state") or {"answers": {}, "current_index": 1, "question_keys": {}}
    answers = risk_state.get("answers") or {}
    current_index = risk_state.get("current_index", 1)
    question_keys = risk_state.get("question_keys") or {}

    answer_key = key or question_keys.get(question_id, question_id)
    if answer != "skip":
        answers[answer_key] = answer

    next_index = current_index + 1
    risk_state.update({"answers": answers, "current_index": next_index, "question_keys": question_keys})
    await update_session(session_id, {"risk_state": risk_state})

    if next_index > MAX_ASSESSMENT_QUESTIONS:
        risk_profile = await _compute_profile(answers)
        completed = list(session.get("completed_agents") or [])
        if "risk_profiler" not in completed:
            completed.append("risk_profiler")
        risk_assessment = {
            "score": risk_profile["risk_level"],
            "confidence": 0.8,
            "reasoning": risk_profile.get("medgemma_reasoning", ""),
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
        return {"complete": True, "risk_profile": risk_profile, "total": MAX_ASSESSMENT_QUESTIONS}

    question = await generate_next_question(answers, next_index)
    if question:
        question_keys[question["id"]] = question.get("key", question["id"])
        risk_state["question_keys"] = question_keys
        await update_session(session_id, {"risk_state": risk_state})

    return {"complete": False, "question": question, "total": MAX_ASSESSMENT_QUESTIONS}


async def _compute_profile(answers: dict) -> dict:
    medgemma_result, _ = await asyncio.gather(
        _medgemma_assess(answers),
        asyncio.sleep(0),
    )

    risk_level = medgemma_result.get("risk_level", "Moderate")
    if risk_level not in _VALID_LEVELS:
        risk_level = "Moderate"

    cancer_types: list[str] = medgemma_result.get("cancer_types_flagged") or []
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
    Falls back to rule-based scoring on any failure.
    """
    _LS = {
        "within_1yr": "had a cancer screening within the last year",
        "1_3yr": "had a cancer screening 1 to 3 years ago",
        "3_5yr": "had a cancer screening 3 to 5 years ago",
        "over_5yr": "has not had a cancer screening in over 5 years",
        "never": "has never had a cancer screening",
    }
    _HPV = {
        "yes": "vaccinated against HPV",
        "no": "not vaccinated against HPV",
        "unsure": "HPV vaccination status unknown",
    }

    profile_context = _build_profile_context(answers)
    screening_status = _LS.get(answers.get("last_screening", ""), "screening history unknown")
    hpv_status = _HPV.get(answers.get("hpv_vaccine", ""), "")
    hpv_line = f"- HPV vaccine: {hpv_status}" if hpv_status else ""

    full_profile = f"{profile_context}\n- Last screening: {screening_status}"
    if hpv_line:
        full_profile += f"\n{hpv_line}"

    prompt = f"""Assess cancer screening risk for the following patient profile and return structured JSON.

Patient profile:
{full_profile}

Return ONLY valid JSON — no prose, no markdown fences:
{{
  "risk_level": "Moderate",
  "risk_score": 6,
  "cancer_types_flagged": ["colorectal"],
  "screening_gap_years": 4,
  "reasoning": "One sentence explaining the primary risk factors for this specific person.",
  "recommendations": "One sentence on the most urgent recommended next step for this person."
}}

Guidelines:
- risk_level must be exactly one of: Low, Moderate, High, Urgent
- Flag High or Urgent if the person has a family history of that cancer type AND a screening gap > 3 years
- cancer_types_flagged must reflect this person's actual risk factors (age, gender, family history, smoking)
- Do not list cancer types unrelated to this person's profile
- This is for health awareness only, not clinical diagnosis"""

    try:
        import google.generativeai as genai
        gemini._configure()
        m = genai.GenerativeModel(
            gemini.MEDGEMMA_MODEL,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        raw = await gemini._generate_with_retry(m, prompt)
        return json.loads(raw)
    except Exception as exc:
        logger.warning(
            "Risk assessment Gemini failed (model=%s): %s — using rule-based fallback",
            gemini.MEDGEMMA_MODEL, exc,
        )
        return _rule_based_fallback(answers)


def _rule_based_fallback(answers: dict) -> dict:
    """Deterministic fallback used when MedGemma is unavailable or returns invalid JSON."""
    score = 0
    cancer: set[str] = set()
    gender = answers.get("gender", "")

    fh = answers.get("family_history", "")
    if fh == "yes_breast_ovarian":
        score += 3; cancer.update(["breast", "ovarian"])
    elif fh == "yes_cervical":
        score += 3; cancer.add("cervical")
    elif fh == "yes_colorectal":
        score += 3; cancer.add("colorectal")
    elif fh == "yes_other":
        score += 1

    ls = answers.get("last_screening", "never")
    score += {"never": 4, "over_5yr": 3, "3_5yr": 2, "1_3yr": 1, "within_1yr": 0}.get(ls, 0)
    score += {"no": 2, "unsure": 1, "yes": 0}.get(answers.get("hpv_vaccine", "no"), 0)
    score += {"current": 2, "former": 1, "never": 0}.get(answers.get("smoking", "never"), 0)
    score += {"45_54": 2, "55_plus": 3, "35_44": 1}.get(answers.get("age_group", ""), 0)

    if gender == "male":
        age_group = answers.get("age_group", "")
        if age_group in ("45_54", "55_plus"):
            cancer.add("colorectal")
            if age_group == "55_plus":
                cancer.add("prostate")
        if answers.get("smoking") in ("current", "former"):
            cancer.add("lung")
    elif gender == "female":
        cancer.add("cervical")
    else:
        cancer.add("colorectal")

    gap = {"within_1yr": 1, "1_3yr": 2, "3_5yr": 4, "over_5yr": 6, "never": None}.get(ls)
    level = "Urgent" if score >= 10 else "High" if score >= 7 else "Moderate" if score >= 4 else "Low"

    return {
        "risk_level": level,
        "risk_score": score,
        "cancer_types_flagged": sorted(cancer),
        "screening_gap_years": gap,
        "reasoning": "Assessed from screening history, family history, and known clinical risk factors.",
        "recommendations": "Schedule a free screening at the nearest government hospital.",
    }


def _summary_prompt(answers: dict, risk_level: str, cancer_types: list, reasoning: str) -> str:
    name = answers.get("user_name") or ""
    gender = answers.get("gender", "")
    age = _AGE_LABELS.get(answers.get("age_group", ""), "")
    fh = _FH_LABELS.get(answers.get("family_history", ""), "")
    smoking = answers.get("smoking", "")
    location = answers.get("location", "")
    types_text = " and ".join(cancer_types) if cancer_types else "cancer"

    context_parts = []
    if age:
        context_parts.append(f"aged {age}")
    if gender and gender != "other":
        context_parts.append(gender)
    if fh and "no known" not in fh:
        context_parts.append(f"with {fh}")
    if smoking == "current":
        context_parts.append("a current smoker")
    if location:
        context_parts.append(f"based in {location}")
    person_context = ", ".join(context_parts) if context_parts else "this person"

    name_line = f"Their name is {name}." if name else ""

    return f"""You are VERA, a warm and caring health companion. Write 2-3 sentences in plain, conversational language to explain a cancer risk assessment to a person.

{name_line}
Person: {person_context}.
Medical assessment: {reasoning}
Risk level: {risk_level}. Cancer types to be aware of: {types_text}.

Rules:
- Address the person directly as "you" and "your" throughout
- Reference their actual profile (age, smoking, family history) to make it feel personal and relevant
- Explain what {risk_level} risk means in everyday language — no medical jargon
- End with one genuinely encouraging sentence: a concrete, free action is available
- Never diagnose. Never say "you have cancer." Never alarm unnecessarily.
- Maximum 3 sentences. No em dashes."""


def _build_timeline(answers: dict) -> list[dict]:
    gap_map = {"within_1yr": 2025, "1_3yr": 2024, "3_5yr": 2022, "over_5yr": 2020, "never": None}
    last_year = gap_map.get(answers.get("last_screening", "never"))

    cancer_types = answers.get("cancer_types_flagged") or []
    primary_screening = "colorectal screening" if "colorectal" in cancer_types else "cancer screening"

    timeline: list[dict] = []
    if last_year:
        timeline.append({"year": last_year, "event": "Last cancer screening", "status": "completed"})
        missed = last_year + 3
        while missed < CURRENT_YEAR:
            timeline.append({"year": missed, "event": f"Recommended {primary_screening}", "status": "missed"})
            missed += 3
    else:
        timeline.append({"year": 2020, "event": "First recommended screening (not completed)", "status": "missed"})
        timeline.append({"year": 2023, "event": f"Recommended {primary_screening}", "status": "missed"})

    timeline.append({"year": CURRENT_YEAR, "event": "Now. VERA recommends action.", "status": "urgent"})
    return timeline


async def generate_next_question(answers: dict, question_number: int) -> dict:
    """Generate the next adaptive question using Gemini based on user profile and previous answers."""
    gender = answers.get("gender", "unknown")
    age_group = _AGE_LABELS.get(answers.get("age_group", ""), "unknown")
    bmi = answers.get("bmi")
    bmi_text = f"{bmi:.1f}" if bmi else "not provided"
    location = answers.get("location", "")
    is_final = question_number == MAX_ASSESSMENT_QUESTIONS

    signup_keys = {"user_name", "age_group", "gender", "location", "language",
                   "height_cm", "weight_kg", "date_of_birth", "bmi", "prefilled"}
    prev_answers = {k: v for k, v in answers.items()
                    if k not in signup_keys and v and v != "skip"}
    prev_text = "\n".join(f"  - {k}: {v}" for k, v in prev_answers.items()) if prev_answers else "  None yet"

    gender_note = ""
    if gender == "female":
        gender_note = "\n- For females: consider cervical/Pap smear history if not covered"
    elif gender == "male":
        gender_note = "\n- For males age 45+: consider prostate PSA screening"

    prompt = f"""You are VERA, a caring health companion. Generate question #{question_number} of {MAX_ASSESSMENT_QUESTIONS} for a cancer risk assessment.

Patient profile:
- Gender: {gender}
- Age group: {age_group}
- BMI: {bmi_text}
- Location: {location}

Previous assessment answers:
{prev_text}

Rules:
- Write in VERA's warm, direct voice using "you"/"your"
- Do NOT repeat any already-answered topic
- Cover: family cancer history, last screening, smoking, alcohol, physical activity, or gender/age-specific screenings{gender_note}
- If this IS question {MAX_ASSESSMENT_QUESTIONS}: open-ended health concerns, type=text, optional=true, options=[]
- Otherwise: type=choice, 3-5 short clear options

Return ONLY valid JSON (no markdown fences, no explanation):
{{
  "id": "q{question_number}",
  "question": "Warm question text here?",
  "type": "choice",
  "key": "snake_case_key",
  "options": [{{"value": "val", "label": "Label"}}],
  "optional": false,
  "why_we_ask": "One sentence explaining why this matters for cancer risk."
}}"""

    try:
        raw = await gemini.generate(prompt)
        text = raw.strip()
        if "```" in text:
            for part in text.split("```"):
                stripped = part.strip().lstrip("json").strip()
                if stripped.startswith("{"):
                    text = stripped
                    break
        result = json.loads(text)
        result["id"] = f"q{question_number}"
        if "type" not in result:
            result["type"] = "text" if is_final else "choice"
        if is_final or result.get("type") == "text":
            result["options"] = []
            result["optional"] = True
            result["type"] = "text"
        elif not result.get("options"):
            result["options"] = []
        return result
    except Exception as exc:
        logger.warning("AI question generation failed for q%d: %s — using fallback", question_number, exc)
        return _fallback_question(question_number, answers)


def _fallback_question(question_number: int, answers: dict) -> dict:
    idx = question_number - 1
    if idx < len(QUESTIONS):
        q = dict(format_question(QUESTIONS[idx], answers))
        q["id"] = f"q{question_number}"
        q.setdefault("why_we_ask", "This helps VERA understand your risk profile more accurately.")
        return q
    return {
        "id": f"q{question_number}",
        "question": "Is there anything health-related that has been worrying you lately?",
        "type": "text",
        "key": "symptoms",
        "placeholder": "Share any symptoms or concerns, or tap Skip",
        "options": [],
        "optional": True,
        "why_we_ask": "Any concerns you share help VERA give you more personalised guidance.",
    }
