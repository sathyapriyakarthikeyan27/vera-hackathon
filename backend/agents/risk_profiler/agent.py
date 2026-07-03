"""
Risk Profiler Agent.
Uses Gemini 2.0 Flash for structured medical risk assessment and plain-language summaries.
"""

import datetime
import logging
from typing import Optional

from models.risk import RISK_LEVELS, RISK_LEVEL_RANK
from services.session_store import get_session, update_session
from services import gemini
from . import prompts
from .questions import QUESTIONS, format_question

logger = logging.getLogger(__name__)

def _current_year() -> int:
    return datetime.date.today().year
_VALID_LEVELS = set(RISK_LEVELS)

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
    original_reasoning: str = risk_profile.get("ai_reasoning", "")

    risk_state: dict = session.get("risk_state") or {}
    answers: dict = risk_state.get("answers") or {}

    verdict = await _reconcile_signals(original_score, pending_signals, original_reasoning, answers)

    conflict_obj = None
    if verdict.get("conflict"):
        conflict_obj = {
            "original_score": original_score,
            "new_score": verdict["final_score"],
            "reason": verdict.get("reason", ""),
            # Verdict C keeps the same score but flags uncertainty, so the score
            # did not actually change. Downstream copy uses this to avoid saying
            # "updated from Moderate to Moderate".
            "uncertain": bool(verdict.get("uncertain")) or verdict["final_score"] == original_score,
            "shown_to_user": False,
        }

    updated_risk_assessment = {
        **risk_assessment,
        "score": verdict["final_score"],
        "source": "profile+records",
        "pending_signals": [],
        "reconciled": True,
        "conflict": conflict_obj,
        # Audit trail: which model and prompt produced this reconciliation.
        "model": gemini.GEMINI_FLASH,
        "prompt_version": prompts.RECONCILE_PROMPT_VERSION,
    }

    updated_risk_profile = {**risk_profile, "risk_level": verdict["final_score"]}

    update_payload: dict = {
        "risk_assessment": updated_risk_assessment,
        "risk_profile": updated_risk_profile,
    }
    # Invalidate any cached companion plan so it regenerates with updated risk context
    if verdict.get("conflict"):
        update_payload["companion_output"] = None

    await update_session(session_id, update_payload)

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
    signals_text = "\n".join(
        f"- Severity: {s.get('severity', 'unknown')}, "
        f"Findings: {', '.join(s.get('anomalies') or []) or 'none'}, "
        f"Urgency: {s.get('urgency_flag', False)}, "
        f"Confidence: {s.get('confidence', 0.5)}"
        for s in pending_signals
    )

    profile_context = _build_profile_context(answers)

    prompt = prompts.reconcile_prompt(
        profile_context=profile_context,
        original_score=original_score,
        original_reasoning=original_reasoning,
        signals_text=signals_text,
    )

    try:
        raw = await gemini.generate_json(prompt)
        result = gemini.parse_json(raw)
        if result.get("final_score") not in _VALID_LEVELS:
            result["final_score"] = original_score
        return result
    except Exception:
        any_high = any(s.get("severity") == "high" or s.get("urgency_flag") for s in pending_signals)
        if any_high:
            new_score = "High" if RISK_LEVEL_RANK.get(original_score, 1) < RISK_LEVEL_RANK["High"] else original_score
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
            "confidence": _profile_confidence(answers, risk_profile.get("engine", "")),
            "reasoning": risk_profile.get("ai_reasoning", ""),
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


def _profile_confidence(answers: dict, engine: str) -> float:
    """
    Heuristic confidence: a data-completeness proxy over the answers that
    drive the score, NOT a calibrated probability. Capped at 0.8 because a
    questionnaire-only assessment should never present near-certainty.
    Rule-fallback scoring is cruder than the model path, so it is docked.
    """
    key_drivers = ("age_group", "gender", "family_history", "smoking", "last_screening")
    present = sum(1 for k in key_drivers if answers.get(k))
    confidence = 0.35 + 0.09 * present
    if engine != "gemini":
        confidence -= 0.15
    return round(max(0.2, min(0.8, confidence)), 2)


async def _compute_profile(answers: dict) -> dict:
    gemini_result = await _gemini_assess(answers)

    risk_level = gemini_result.get("risk_level", "Moderate")
    if risk_level not in _VALID_LEVELS:
        risk_level = "Moderate"

    cancer_types: list[str] = gemini_result.get("cancer_types_flagged") or []
    risk_score: int = gemini_result.get("risk_score") or 5
    screening_gap = gemini_result.get("screening_gap_years")
    reasoning = gemini_result.get("reasoning", "")

    timeline = _build_timeline(answers)

    summary = await gemini.generate_safe(
        _summary_prompt(answers, risk_level, cancer_types, reasoning),
        fallback=_FALLBACK_SUMMARY,
    )

    engine = gemini_result.get("engine", "rule_fallback")

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "cancer_types_flagged": cancer_types,
        "screening_gap_years": screening_gap,
        "timeline": timeline,
        "plain_language_summary": summary,
        "ai_reasoning": reasoning,
        # Audit trail: which engine, model, and prompt/rubric versions produced
        # this assessment. "rule_fallback" means Gemini was unavailable and the
        # deterministic rubric scored instead.
        "engine": engine,
        "model": gemini.GEMINI_FLASH if engine == "gemini" else None,
        "prompt_versions": {
            "assess": prompts.ASSESS_PROMPT_VERSION if engine == "gemini" else RUBRIC_VERSION,
            "summary": prompts.SUMMARY_PROMPT_VERSION,
        },
        "disclaimer": (
            "This is not a medical diagnosis. VERA provides risk awareness only. "
            "Please consult a qualified doctor."
        ),
    }


async def _gemini_assess(answers: dict) -> dict:
    """
    Call Gemini Flash for structured medical risk assessment.
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

    prompt = prompts.assess_prompt(full_profile)

    try:
        raw = await gemini.generate_json(prompt, temperature=0.1)
        result = gemini.parse_json(raw)
        if not isinstance(result, dict):
            raise ValueError("assessment output was not a JSON object")
        result["engine"] = "gemini"
        return result
    except Exception as exc:
        logger.warning(
            "Risk assessment failed (model=%s): %s — using rule-based fallback",
            gemini.GEMINI_FLASH, exc,
        )
        return _rule_based_fallback(answers)


# Version tag for the deterministic rubric below. Stored with every fallback
# assessment so scores remain traceable to the exact rule set that produced them.
RUBRIC_VERSION = "fallback-v2"


def _rule_based_fallback(answers: dict) -> dict:
    """
    Deterministic fallback used when Gemini is unavailable or returns invalid JSON.

    Each rule cites the screening guidance that motivates it. The POINT WEIGHTS
    and level thresholds are engineering choices and are NOT clinically
    validated — clinician sign-off is an open gate (no reviewer available yet).
    Awareness-only output; never presented as diagnosis.
    """
    score = 0
    cancer: set[str] = set()
    gender = answers.get("gender", "")
    age_group = answers.get("age_group", "")

    # First-degree family history is the strongest signal we collect: guidance
    # moves screening earlier and more frequent for affected cancer types
    # (e.g. NCCN colorectal: start at 40 with an affected first-degree relative).
    fh = answers.get("family_history", "")
    if fh == "yes_breast_ovarian":
        score += 3; cancer.update(["breast", "ovarian"])
    elif fh == "yes_cervical":
        score += 3; cancer.add("cervical")
    elif fh == "yes_colorectal":
        score += 3; cancer.add("colorectal")
    elif fh == "yes_other":
        score += 1

    # Overdue screening: USPSTF intervals are 1-5 years depending on programme
    # (mammography 2y, cervical 3-5y, colorectal 1-10y by method), so 3+ years
    # unscreened means overdue for most programmes; "never" is furthest overdue.
    ls = answers.get("last_screening", "never")
    score += {"never": 4, "over_5yr": 3, "3_5yr": 2, "1_3yr": 1, "within_1yr": 0}.get(ls, 0)

    # HPV vaccination reduces cervical cancer risk (WHO cervical cancer
    # elimination strategy); relevant to people with a cervix.
    if gender == "female":
        score += {"no": 2, "unsure": 1, "yes": 0}.get(answers.get("hpv_vaccine", "no"), 0)

    # Smoking: primary lung cancer risk factor (USPSTF 2021 LDCT criteria) and
    # elevates risk across several other cancers.
    score += {"current": 2, "former": 1, "never": 0}.get(answers.get("smoking", "never"), 0)

    # Age: screening programmes begin at 40-50 (breast 40, colorectal 45,
    # lung 50) and most cancer incidence rises with age.
    score += {"45_54": 2, "55_plus": 3, "35_44": 1}.get(age_group, 0)

    # Obesity is an established risk factor for several cancers (IARC 2016
    # handbook: colorectal, breast, and others).
    bmi = answers.get("bmi")
    if isinstance(bmi, (int, float)) and bmi >= 30:
        score += 1

    # Cancer types to monitor, by guideline age/eligibility:
    if age_group in ("45_54", "55_plus"):
        cancer.add("colorectal")            # USPSTF 2021: screen from 45
    if gender == "male" and age_group == "55_plus":
        cancer.add("prostate")              # USPSTF 2018: discuss at 55-69
    if answers.get("smoking") in ("current", "former"):
        cancer.add("lung")                  # USPSTF 2021 LDCT criteria signal
    if gender == "female":
        cancer.add("cervical")              # USPSTF/WHO: screen 21-65
        if age_group in ("45_54", "55_plus"):
            cancer.add("breast")            # USPSTF 2024: mammography 40-74
    if not cancer:
        cancer.add("colorectal")

    # A reported symptom or concern always warrants at least a Moderate
    # recommendation to get it looked at (VERA never triages symptoms itself).
    symptoms = answers.get("symptoms")
    has_symptoms = bool(symptoms) and symptoms != "skip"
    if has_symptoms:
        score = max(score, 4)

    gap = {"within_1yr": 1, "1_3yr": 2, "3_5yr": 4, "over_5yr": 6, "never": None}.get(ls)
    level = "Urgent" if score >= 10 else "High" if score >= 7 else "Moderate" if score >= 4 else "Low"

    return {
        "risk_level": level,
        "risk_score": score,
        "cancer_types_flagged": sorted(cancer),
        "screening_gap_years": gap,
        "reasoning": "Assessed from screening history, family history, and known clinical risk factors.",
        "recommendations": "Schedule a free screening at the nearest government hospital.",
        "engine": "rule_fallback",
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

    return prompts.summary_prompt(
        name_line=name_line,
        person_context=person_context,
        reasoning=reasoning,
        risk_level=risk_level,
        types_text=types_text,
    )


def _build_timeline(answers: dict) -> list[dict]:
    year = _current_year()
    # Offsets from the current year for each screening-recency answer.
    gap_offsets = {"within_1yr": 0, "1_3yr": 1, "3_5yr": 3, "over_5yr": 5, "never": None}
    offset = gap_offsets.get(answers.get("last_screening", "never"))
    last_year = year - offset if offset is not None else None

    cancer_types = answers.get("cancer_types_flagged") or []
    primary_screening = "colorectal screening" if "colorectal" in cancer_types else "cancer screening"

    timeline: list[dict] = []
    if last_year:
        timeline.append({"year": last_year, "event": "Last cancer screening", "status": "completed"})
        missed = last_year + 3
        while missed < year:
            timeline.append({"year": missed, "event": f"Recommended {primary_screening}", "status": "missed"})
            missed += 3
    else:
        timeline.append({"year": year - 5, "event": "First recommended screening (not completed)", "status": "missed"})
        timeline.append({"year": year - 2, "event": f"Recommended {primary_screening}", "status": "missed"})

    timeline.append({"year": year, "event": "Now. VERA recommends action.", "status": "urgent"})
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

    prompt = prompts.next_question_prompt(
        question_number=question_number,
        max_questions=MAX_ASSESSMENT_QUESTIONS,
        gender=gender,
        age_group=age_group,
        bmi_text=bmi_text,
        location=location,
        prev_text=prev_text,
        gender_note=gender_note,
    )

    try:
        raw = await gemini.generate_json(prompt, temperature=0.4)
        result = gemini.parse_json(raw)
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
