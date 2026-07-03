"""
Companion Agent (Agent 4).
Uses Gemini to build a personalised follow-up plan, multilingual family message
drafts, and a reminder schedule based on the full session.
"""

import asyncio
import datetime
import json
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini
from . import prompts


def _today() -> str:
    return datetime.date.today().isoformat()


def _offset(days: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


_AGE_LABELS = {
    "under_25": "under 25", "25_34": "25 to 34", "35_44": "35 to 44",
    "45_54": "45 to 54", "55_plus": "over 55",
}


def _build_person_context(answers: dict, risk_level: str, cancer_types: list) -> str:
    parts = []
    if age := _AGE_LABELS.get(answers.get("age_group", "")):
        parts.append(f"Age: {age}")
    if gender := answers.get("gender"):
        parts.append(f"Gender: {gender}")
    if cancer_types:
        parts.append(f"Cancer risk types: {', '.join(cancer_types)}")
    if risk_level:
        parts.append(f"Risk level: {risk_level}")
    if answers.get("smoking") == "current":
        parts.append("Current smoker")
    if loc := answers.get("location"):
        parts.append(f"Location: {loc}")
    return "\n".join(f"- {p}" for p in parts)


def _fallback_follow_up() -> list:
    return [
        {"date": _offset(7), "action": "Call your nearest government hospital to book a free cancer screening appointment", "location": None, "contact": None},
        {"date": _offset(14), "action": "Confirm your appointment and write down any questions you want to ask the doctor", "location": None, "contact": None},
        {"date": _offset(29), "action": "Attend your cancer screening appointment", "location": None, "contact": None},
        {"date": _offset(45), "action": "Follow up with your doctor on the screening results", "location": None, "contact": None},
    ]


def _fallback_reminders() -> list:
    return [
        {"date": _offset(4), "message": "Have you booked your free cancer screening yet? I'm here to help if you need it."},
        {"date": _offset(24), "message": "Your screening appointment is coming up soon. You are doing the right thing."},
        {"date": _offset(45), "message": "Time to follow up on your screening results. Call your doctor today."},
    ]

_FALLBACK_MESSAGES = {
    "en": (
        "Hi, I just completed a quick cancer risk check with VERA and learned I should book "
        "a free screening soon. It won't take long. Would you come with me to the appointment? "
        "Having you there would mean a lot."
    ),
    "hi": (
        "नमस्ते, मैंने अभी VERA के साथ एक कैंसर जोखिम जाँच पूरी की और पता चला कि मुझे जल्द ही "
        "एक मुफ्त जाँच करवानी चाहिए। क्या आप मेरे साथ अपॉइंटमेंट पर चल सकते हैं? "
        "आपका साथ होना मेरे लिए बहुत मायने रखता है।"
    ),
    "ta": (
        "வணக்கம், நான் இப்போது VERA உடன் ஒரு புற்றுநோய் அபாய பரிசோதனையை முடித்தேன், "
        "விரைவில் ஒரு இலவச பரிசோதனை எடுக்க வேண்டும் என்று தெரிந்தது. "
        "என்னுடன் சந்திப்புக்கு வர முடியுமா? உங்கள் துணை எனக்கு மிகவும் முக்கியம்."
    ),
}


async def generate_followup(session_id: str) -> Optional[dict]:
    session = await get_session(session_id)
    if not session:
        return None

    if session.get("companion_output"):
        return session["companion_output"]

    risk_profile = session.get("risk_profile") or {}
    risk_level: str = risk_profile.get("risk_level", "Moderate")
    cancer_types: list = risk_profile.get("cancer_types_flagged") or []
    user_name: str = session.get("user_name") or ""

    risk_state: dict = session.get("risk_state") or {}
    answers: dict = risk_state.get("answers") or {}
    location: str = answers.get("location") or "India"

    schemes_output: dict = session.get("schemes_output") or {}
    clinics: list = schemes_output.get("nearest_clinics") or []
    top_clinic = clinics[0] if clinics else None
    recommended_specialist = schemes_output.get("recommended_specialist", "Oncologist")

    risk_assessment: dict = session.get("risk_assessment") or {}
    conflict: Optional[dict] = risk_assessment.get("conflict")

    records_output: dict = session.get("records_output") or {}
    document_type: str = records_output.get("document_type", "")
    document_filename: str = records_output.get("filename", "")
    doc_label: str = document_filename or document_type or "uploaded medical document"

    plan_result, messages_result = await asyncio.gather(
        _generate_plan(
            user_name, risk_level, cancer_types, location,
            top_clinic, recommended_specialist, answers,
            conflict=conflict,
            document_type=document_type,
            document_filename=document_filename,
        ),
        _generate_family_messages(risk_level, cancer_types, top_clinic, answers),
    )

    output = {
        "greeting": plan_result.get("greeting", _default_greeting(user_name, conflict, doc_label)),
        "follow_up_plan": plan_result.get("follow_up_plan", _fallback_follow_up()),
        "reminder_schedule": plan_result.get("reminder_schedule", _fallback_reminders()),
        "family_message_drafts": messages_result,
        "conflict_context": {
            "triggered": bool(conflict),
            "uncertain": bool(conflict.get("uncertain")) if conflict else False,
            "original_score": conflict.get("original_score") if conflict else None,
            "new_score": conflict.get("new_score") if conflict else None,
            "document_type": document_type or None,
            "document_filename": document_filename or None,
        },
    }

    completed = list(session.get("completed_agents") or [])
    if "companion_agent" not in completed:
        completed.append("companion_agent")

    # Re-read before persisting. A reconciliation may have escalated the risk
    # (and invalidated companion_output) while we were calling Gemini. If the
    # score changed under us, this plan was built from a now-stale risk level,
    # so discard it and let the next request regenerate against the new score.
    latest = await get_session(session_id)
    if latest:
        latest_score = (latest.get("risk_profile") or {}).get("risk_level", risk_level)
        if latest_score != risk_level:
            return latest.get("companion_output")

    await update_session(session_id, {"companion_output": output, "completed_agents": completed})
    return output


async def _generate_plan(
    user_name: str,
    risk_level: str,
    cancer_types: list,
    location: str,
    clinic: Optional[dict],
    specialist: str,
    answers: dict,
    conflict: Optional[dict] = None,
    document_type: str = "",
    document_filename: str = "",
) -> dict:
    person_context = _build_person_context(answers, risk_level, cancer_types)
    types_text = " and ".join(cancer_types) if cancer_types else "cancer"
    clinic_info = (
        f"Nearest recommended clinic: {clinic['name']} at {clinic['address']}. "
        f"Contact: {clinic.get('contact', 'not listed')}."
        if clinic
        else f"Nearest free government hospital in {location}."
    )
    name_line = f"Their name is {user_name}." if user_name else ""

    doc_label = document_filename or document_type or "uploaded medical document"

    prompt = prompts.plan_prompt(
        name_line=name_line,
        person_context=person_context,
        specialist=specialist,
        clinic_info=clinic_info,
        today=_today(),
        types_text=types_text,
        location=location,
        risk_level=risk_level,
        doc_label=doc_label,
        conflict=conflict,
    )

    try:
        raw = await gemini.generate_json(prompt, temperature=0.4)
        return gemini.parse_json(raw)
    except Exception:
        return {
            "greeting": _default_greeting(user_name, conflict, doc_label),
            "follow_up_plan": _fallback_follow_up(),
            "reminder_schedule": _fallback_reminders(),
        }


async def _generate_family_messages(
    risk_level: str, cancer_types: list, clinic: Optional[dict], answers: dict
) -> dict:
    clinic_name = clinic["name"] if clinic else "your nearest government hospital"
    types_text = " and ".join(cancer_types) if cancer_types else "cancer"
    gender = answers.get("gender", "")
    age = _AGE_LABELS.get(answers.get("age_group", ""), "")

    context_parts = []
    if age:
        context_parts.append(f"aged {age}")
    if gender and gender != "other":
        context_parts.append(gender)
    person_context = " ".join(context_parts) if context_parts else "person"

    prompt = prompts.family_messages_prompt(person_context, risk_level, types_text, clinic_name)

    try:
        raw = await gemini.generate_json(prompt, temperature=0.4)
        result = gemini.parse_json(raw)
        return {
            "en": result.get("en", _FALLBACK_MESSAGES["en"]),
            "hi": result.get("hi", _FALLBACK_MESSAGES["hi"]),
            "ta": result.get("ta", _FALLBACK_MESSAGES["ta"]),
        }
    except Exception:
        return _FALLBACK_MESSAGES


def _default_greeting(user_name: str, conflict: Optional[dict] = None, doc_label: str = "") -> str:
    name = f" {user_name}" if user_name else ""
    if conflict and conflict.get("uncertain"):
        doc = doc_label or "your uploaded report"
        return (
            f"Hi{name}, your {doc} surfaced some findings that need a closer look. "
            "Your risk level has not changed, but I have put together a plan so a "
            "specialist can review these findings with you soon."
        )
    if conflict:
        original = conflict.get("original_score", "Moderate")
        new_score = conflict.get("new_score", "High")
        doc = doc_label or "your uploaded report"
        return (
            f"Hi{name}, your {doc} has given me a clearer picture of your situation. "
            f"Based on what it showed, I have updated your risk from {original} to {new_score}. "
            "I have put together an updated plan so you can take the right next steps quickly."
        )
    return (
        f"Hi{name}, taking this step for your health took real courage. "
        "I have put together a simple plan to help you move from awareness to action."
    )
