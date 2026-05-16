"""
Companion Agent.
Uses Gemini to build a personalised follow-up plan, multilingual family message
drafts (English, Hindi, Tamil), and a reminder schedule based on the full session.
"""

import asyncio
import json
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini

_CURRENT_DATE = "2026-05-14"

_FALLBACK_FOLLOW_UP = [
    {
        "date": "2026-05-21",
        "action": "Call your nearest government hospital to book a free Pap smear",
        "location": None,
        "contact": None,
    },
    {
        "date": "2026-05-28",
        "action": "Confirm your appointment and prepare any questions for the doctor",
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
        "action": "Follow up on your results with your doctor",
        "location": None,
        "contact": None,
    },
]

_FALLBACK_REMINDERS = [
    {"date": "2026-05-18", "message": "Have you booked your free cancer screening yet?"},
    {"date": "2026-06-10", "message": "Your screening appointment is coming up soon — you've got this."},
    {"date": "2026-07-01", "message": "Time to check your screening results. Call your doctor today."},
]

_FALLBACK_MESSAGES = {
    "en": (
        "Hi, I just completed a quick cancer risk check with VERA and learned I should book "
        "a free Pap smear soon. It won't take long — would you come with me to the appointment? "
        "Having you there would mean a lot."
    ),
    "hi": (
        "नमस्ते, मैंने अभी VERA के साथ एक कैंसर जोखिम जाँच पूरी की और पता चला कि मुझे जल्द ही "
        "एक मुफ्त Pap smear करवाना चाहिए। क्या आप मेरे साथ अपॉइंटमेंट पर चल सकती हैं? "
        "आपका साथ होना मेरे लिए बहुत मायने रखता है।"
    ),
    "ta": (
        "வணக்கம், நான் இப்போது VERA உடன் ஒரு புற்றுநோய் அபாய பரிசோதனையை முடித்தேன், "
        "விரைவில் ஒரு இலவச Pap smear எடுக்க வேண்டும் என்று தெரிந்தது. "
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
    cancer_types: list = risk_profile.get("cancer_types_flagged") or ["cervical"]
    user_name: str = session.get("user_name") or ""

    risk_state: dict = session.get("risk_state") or {}
    answers: dict = risk_state.get("answers") or {}
    location: str = answers.get("location") or "India"

    schemes_output: dict = session.get("schemes_output") or {}
    clinics: list = schemes_output.get("nearest_clinics") or []
    top_clinic = clinics[0] if clinics else None

    plan_result, messages_result = await asyncio.gather(
        _generate_plan(user_name, risk_level, cancer_types, location, top_clinic),
        _generate_family_messages(risk_level, top_clinic),
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
) -> dict:
    types_text = " and ".join(cancer_types) if cancer_types else "cervical cancer"
    clinic_info = (
        f"Nearest clinic: {clinic['name']} at {clinic['address']}. Contact: {clinic.get('contact', 'not available')}."
        if clinic
        else f"Nearest free government hospital in {location}."
    )
    name_line = f"Her name is {user_name}." if user_name else ""

    prompt = f"""You are VERA's Companion Agent. Create a personalised follow-up plan.

{name_line}
Risk level: {risk_level}. Cancer types: {types_text}.
Location: {location}.
{clinic_info}
Today's date: {_CURRENT_DATE}.

Return ONLY this JSON structure — no markdown:
{{
  "greeting": "1-2 warm sentences acknowledging her courage. Address by name if given.",
  "follow_up_plan": [
    {{
      "date": "YYYY-MM-DD",
      "action": "Specific, concrete action step",
      "location": "Place name or null",
      "contact": "Phone number or null"
    }}
  ],
  "reminder_schedule": [
    {{
      "date": "YYYY-MM-DD",
      "message": "Short, warm reminder text"
    }}
  ]
}}

Include 3-4 follow-up steps over the next 6 weeks. Include 3 reminders at key moments."""

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


async def _generate_family_messages(risk_level: str, clinic: Optional[dict]) -> dict:
    clinic_name = clinic["name"] if clinic else "your nearest government hospital"

    prompt = f"""You are VERA. Draft a short, warm message for a woman to send to a trusted family member or friend.

Context: She has {risk_level} cancer risk and needs to book a free screening at {clinic_name}.

The message should be 2-3 sentences, non-alarming, explain she is taking a positive health step, and ask for support or accompaniment.

Return ONLY this JSON — no markdown:
{{
  "en": "English message (2-3 sentences)",
  "hi": "Hindi message in Devanagari script (2-3 sentences)",
  "ta": "Tamil message in Tamil script (2-3 sentences)"
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
    name = f", {user_name}" if user_name else ""
    return (
        f"Welcome back{name} — taking this step for your health took real courage. "
        "I've put together a simple plan to help you move from awareness to action."
    )
