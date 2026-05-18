"""
Scheme Navigator Agent (Agent 2).
Uses pgvector for semantic scheme search first, falls back to Gemini generation.
All scheme data is synthetic JSON seeded at startup — no real government APIs called.
"""

import asyncio
import json
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini
from services.database import search_schemes

_AGE_LABELS = {
    "under_25": "under 25", "25_34": "25 to 34", "35_44": "35 to 44",
    "45_54": "45 to 54", "55_plus": "over 55",
}


def _parse_json_array(raw: str) -> list:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _scheme_row_to_output(row: dict) -> dict:
    meta = row.get("metadata") or {}
    return {
        "scheme_name": row["scheme_name"],
        "description": row["content"],
        "eligibility_summary": meta.get("eligibility", "Varies by location"),
        "coverage": meta.get("coverage", "Cancer screening"),
        "url": meta.get("url"),
    }


def _build_person_description(answers: dict, risk_level: str, cancer_types: list) -> str:
    """Build a concise, personalized description used in prompts."""
    parts = []
    if age := _AGE_LABELS.get(answers.get("age_group", "")):
        parts.append(age)
    if gender := answers.get("gender"):
        parts.append(gender)
    parts.append(f"with {risk_level.lower()} cancer risk")
    if cancer_types:
        parts.append(f"for {' and '.join(cancer_types)}")
    return " ".join(parts)


def _specialist_for_cancer_types(cancer_types: list, risk_level: str) -> str:
    """Determine the right specialist based on cancer signal, consistent with CLAUDE.md routing."""
    if not cancer_types:
        return "Oncologist"
    type_set = set(t.lower() for t in cancer_types)
    if "colorectal" in type_set or "bowel" in type_set:
        return "Gastroenterologist"
    if "breast" in type_set or "ovarian" in type_set or "cervical" in type_set or "gynaecologic" in type_set:
        return "Gynaecologic Oncologist"
    if "lung" in type_set and "smoking" in type_set:
        return "Pulmonologist"
    if "skin" in type_set:
        return "Dermatologist"
    if "prostate" in type_set:
        return "Urologist"
    return "Oncologist"


async def match(session_id: str) -> Optional[dict]:
    session = await get_session(session_id)
    if not session:
        return None

    if session.get("schemes_output"):
        return session["schemes_output"]

    risk_state: dict = session.get("risk_state") or {}
    answers: dict = risk_state.get("answers") or {}
    location: str = answers.get("location") or "India"
    risk_profile: dict = session.get("risk_profile") or {}
    risk_level: str = risk_profile.get("risk_level", "Moderate")
    cancer_types: list = risk_profile.get("cancer_types_flagged") or []
    specialist = _specialist_for_cancer_types(cancer_types, risk_level)

    schemes_result, clinics_result = await asyncio.gather(
        _find_schemes(location, risk_level, cancer_types, answers),
        _find_clinics(location, cancer_types, specialist, answers),
    )

    output = {
        "matched_schemes": schemes_result,
        "nearest_clinics": clinics_result,
        "recommended_specialist": specialist,
    }

    completed = list(session.get("completed_agents") or [])
    if "scheme_navigator" not in completed:
        completed.append("scheme_navigator")

    await update_session(session_id, {"schemes_output": output, "completed_agents": completed})
    return output


async def _find_schemes(
    location: str, risk_level: str, cancer_types: list, answers: dict
) -> list[dict]:
    """Try pgvector semantic search first; fall back to Gemini generation."""
    try:
        query = f"{location} cancer screening scheme {' '.join(cancer_types)} {risk_level} risk"
        embedding = await gemini.embed_text(query)
        rows = await search_schemes(embedding, location, limit=4)
        if rows:
            return [_scheme_row_to_output(r) for r in rows]
    except Exception:
        pass
    return await _research_schemes_gemini(location, risk_level, cancer_types, answers)


async def _research_schemes_gemini(
    location: str, risk_level: str, cancer_types: list, answers: dict
) -> list[dict]:
    person = _build_person_description(answers, risk_level, cancer_types)
    types_text = " and ".join(cancer_types) if cancer_types else "cancer"
    gender = answers.get("gender", "")
    age_group = answers.get("age_group", "")

    gender_note = ""
    if gender == "male":
        gender_note = "Include schemes relevant for men if applicable (e.g. prostate, colorectal)."
    elif gender == "female":
        gender_note = "Include schemes relevant for women if applicable (e.g. cervical, breast, gynaecologic)."

    prompt = f"""Find the 3 to 4 most relevant government and non-profit health schemes for someone in {location} who is {person}.

The person is specifically at risk for: {types_text}.
{gender_note}

If the location is in India, prioritise: Ayushman Bharat PM-JAY, National Cancer Screening Programme (NCSP), state health missions, CGHS.
For UK: NHS cancer screening programmes. For Egypt: NHIA (National Health Insurance Authority). For other countries, find equivalent national cancer screening programmes.

For each scheme, explain in the "why_matches" field exactly why this scheme is relevant to this specific person's age, gender, and cancer risk type. Not a generic statement.

Return a JSON array only. No markdown:
[
  {{
    "scheme_name": "Full official scheme name",
    "description": "2 sentences: what it covers and who runs it",
    "eligibility_summary": "1 sentence on who qualifies, specific to this person if possible",
    "coverage": "Cancer screenings covered",
    "url": "Official website URL if known, else null",
    "why_matches": "One warm, specific sentence on why this scheme is relevant to this person's age, gender, and cancer risk"
  }}
]

Return ONLY the JSON array."""

    fallback = [
        {
            "scheme_name": "Ayushman Bharat: Pradhan Mantri Jan Arogya Yojana (PM-JAY)",
            "description": "India's flagship government health insurance covering secondary and tertiary care for economically vulnerable families. Administered by the National Health Authority.",
            "eligibility_summary": "Families identified in SECC database, approximately 50 crore beneficiaries across India.",
            "coverage": f"Cancer screening and treatment at empanelled hospitals. Covers {types_text} screening.",
            "url": "https://pmjay.gov.in",
            "why_matches": f"PM-JAY covers cancer screening at no cost, which is directly relevant for someone with your {risk_level.lower()} risk profile for {types_text}.",
        },
        {
            "scheme_name": "National Cancer Screening Programme (NCSP)",
            "description": "Government of India programme for early detection of oral, cervical, colorectal, and breast cancers at primary health centres. Part of the National Health Mission.",
            "eligibility_summary": "Adults across India, available at government health centres. Priority for ages 30 to 65.",
            "coverage": f"Free cancer screening for {types_text}.",
            "url": "https://nhm.gov.in",
            "why_matches": f"NCSP provides free targeted screening for {types_text} at your nearest government health centre.",
        },
    ]

    try:
        raw = await gemini.generate(prompt)
        return _parse_json_array(raw)
    except Exception:
        return fallback


async def _find_clinics(
    location: str, cancer_types: list, specialist: str, answers: dict
) -> list[dict]:
    types_text = ", ".join(cancer_types) if cancer_types else "cancer"
    person = _build_person_description(answers, "", cancer_types)
    gender = answers.get("gender", "")
    gender_pref = ""
    if gender == "female":
        gender_pref = "Note if female doctors are available, as this may be important."

    prompt = f"""Find 3 real, reputable government hospitals or free cancer screening centres in or near {location} that offer free {types_text} screening or {specialist} consultations.

The person seeking care is: {person}.
{gender_pref}

Prioritise: AIIMS, government district hospitals, Tata Memorial Hospital, state cancer institutes, Regional Cancer Centres, NHS hospitals (UK), NHIA-accredited hospitals (Egypt).
Only include real hospitals with accurate addresses.

Return a JSON array of exactly 3 clinics — no markdown:
[
  {{
    "name": "Official hospital or clinic name",
    "address": "Full address including city and state or country",
    "services": ["{specialist} consultation", "Cancer screening"],
    "cost": "Free",
    "female_doctor_available": true,
    "contact": "Phone or helpline if known, else null",
    "appointment_url": "URL to book if available, else null",
    "distance_km": 5.0
  }}
]"""

    fallback = [
        {
            "name": "AIIMS: All India Institute of Medical Sciences",
            "address": "Sri Aurobindo Marg, Ansari Nagar, New Delhi 110029",
            "services": [specialist, "Cancer Screening OPD", "Diagnostic Imaging"],
            "cost": "Free",
            "female_doctor_available": True,
            "contact": "011-26588500",
            "appointment_url": "https://aiimsdelhi.org",
            "distance_km": 8.0,
        },
        {
            "name": "Tata Memorial Hospital",
            "address": "Dr Ernest Borges Road, Parel, Mumbai 400012",
            "services": [specialist, "Oncology OPD", "Cancer Screening"],
            "cost": "Free",
            "female_doctor_available": True,
            "contact": "022-24177000",
            "appointment_url": "https://tmc.gov.in",
            "distance_km": 15.0,
        },
        {
            "name": "Safdarjung Hospital",
            "address": "Ring Road, Safdarjung, New Delhi 110029",
            "services": [specialist, "Cancer Screening OPD"],
            "cost": "Free",
            "female_doctor_available": True,
            "contact": "011-26165060",
            "appointment_url": None,
            "distance_km": 10.0,
        },
    ]

    try:
        raw = await gemini.generate(prompt)
        return _parse_json_array(raw)
    except Exception:
        return fallback
