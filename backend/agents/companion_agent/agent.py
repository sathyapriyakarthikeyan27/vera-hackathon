"""
Companion Agent (Agent 4).
Uses Gemini to build a personalised follow-up plan, multilingual family message
drafts, and a reminder schedule based on the full session.
"""

import asyncio
import json
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini

_CURRENT_DATE = "2026-05-17"

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


_FALLBACK_FOLLOW_UP = [
    {
        "date": "2026-05-24",
        "action": "Call your nearest government hospital to book a free cancer screening appointment",
        "location": None,
        "contact": None,
    },
    {
        "date": "2026-05-31",
        "action": "Confirm your appointment and write down any questions you want to ask the doctor",
        "location": None,
        "contact": None,
    },
    {
        "date": "2026-06-15",
        "action": "Attend your cancer screening appointment",
        "location": None,
        "contact": None,
    },
    {
        "date": "2026-07-01",
        "action": "Follow up with your doctor on the screening results",
        "location": None,
        "contact": None,
    },
]

_FALLBACK_REMINDERS = [
    {"date": "2026-05-21", "message": "Have you booked your free cancer screening yet? I'm here to help if you need it."},
    {"date": "2026-06-10", "message": "Your screening appointment is coming up soon. You are doing the right thing."},
    {"date": "2026-07-01", "message": "Time to follow up on your screening results. Call your doctor today."},
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

    plan_result, messages_result = await asyncio.gather(
        _generate_plan(user_name, risk_level, cancer_types, location, top_clinic, recommended_specialist, answers),
        _generate_family_messages(risk_level, cancer_types, top_clinic, answers),
    )

    output = {
        "greeting": plan_result.get("greeting", _default_greeting(user_name)),
        "follow_up_plan": plan_result.get("follow_up_plan", _FALLBACK_FOLLOW_UP),
        "reminder_schedule": plan_result.get("reminder_schedule", _FALLBACK_REMINDERS),
        "family_message_drafts": messages_result,
    }

    completed = list(session.get("completed_agents") or [])
    if "companion_agent" not in completed:
        completed.append("companion_agent")

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

    prompt = f"""Create a warm, personalised cancer screening follow-up plan for a real person.

{name_line}
Person profile:
{person_context}

Recommended specialist: {specialist}
{clinic_info}
Today's date: {_CURRENT_DATE}.

The plan must feel personal. Reference their specific risk type ({types_text}) and their location ({location}).
Use "you" and "your" throughout.

Return ONLY this JSON. No markdown:
{{
  "greeting": "1-2 warm sentences acknowledging their specific situation. Reference their name if given, their cancer risk type, and that taking this step shows courage. No em dashes.",
  "follow_up_plan": [
    {{
      "date": "YYYY-MM-DD",
      "action": "Specific, actionable step. Reference the specialist type and their specific cancer risk.",
      "location": "Clinic or hospital name if relevant, else null",
      "contact": "Phone number if available, else null"
    }}
  ],
  "reminder_schedule": [
    {{
      "date": "YYYY-MM-DD",
      "message": "Short, warm reminder that feels personal to this person. No em dashes."
    }}
  ]
}}

Include 3 to 4 follow-up steps over 6 weeks. Include 3 reminder messages at key moments."""

    try:
        raw = await gemini.generate(prompt)
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return {
            "greeting": _default_greeting(user_name),
            "follow_up_plan": _FALLBACK_FOLLOW_UP,
            "reminder_schedule": _FALLBACK_REMINDERS,
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

    prompt = f"""Draft a short, warm message for a {person_context} to send to a trusted family member or close friend asking for support.

Context: They have {risk_level.lower()} risk for {types_text} and need to book a free cancer screening at {clinic_name}.

The message should:
- Be 2 to 3 sentences
- Feel natural, not medical or clinical
- Explain they are taking a positive health step
- Ask for support or accompaniment in a gentle way
- Not mention cancer in an alarming way

Return ONLY this JSON. No markdown:
{{
  "en": "Natural English message (2-3 sentences, no em dashes)",
  "hi": "Natural Hindi message in Devanagari script (2-3 sentences)",
  "ta": "Natural Tamil message in Tamil script (2-3 sentences)"
}}"""

    try:
        raw = await gemini.generate(prompt)
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        return {
            "en": result.get("en", _FALLBACK_MESSAGES["en"]),
            "hi": result.get("hi", _FALLBACK_MESSAGES["hi"]),
            "ta": result.get("ta", _FALLBACK_MESSAGES["ta"]),
        }
    except Exception:
        return _FALLBACK_MESSAGES


def _default_greeting(user_name: str) -> str:
    name = f" {user_name}" if user_name else ""
    return (
        f"Hi{name}, taking this step for your health took real courage. "
        "I've put together a simple plan to help you move from awareness to action."
    )
