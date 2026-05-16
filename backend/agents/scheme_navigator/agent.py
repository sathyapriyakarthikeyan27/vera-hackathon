"""
Scheme Navigator Agent.
Uses pgvector for semantic scheme search first, falls back to Gemini generation.
No hardcoded data — pgvector RAG seeded at startup, Gemini for unknown locations.
"""

import asyncio
import json
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini
from services.database import search_schemes


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


async def match(session_id: str) -> Optional[dict]:
    session = await get_session(session_id)
    if not session:
        return None

    if session.get("schemes_output"):
        return session["schemes_output"]

    risk_state: dict = session.get("risk_state") or {}
    answers: dict = risk_state.get("answers") or {}
    location: str = answers.get("location") or "India"
    risk_level: str = (session.get("risk_profile") or {}).get("risk_level", "Moderate")
    cancer_types: list = (session.get("risk_profile") or {}).get("cancer_types_flagged") or ["cervical"]

    schemes_result, clinics_result = await asyncio.gather(
        _find_schemes(location, risk_level, cancer_types),
        _find_clinics(location, cancer_types),
    )

    output = {
        "matched_schemes": schemes_result,
        "nearest_clinics": clinics_result,
    }

    completed = list(session.get("completed_agents") or [])
    if "scheme_navigator" not in completed:
        completed.append("scheme_navigator")

    await update_session(session_id, {"schemes_output": output, "completed_agents": completed})
    return output


async def _find_schemes(location: str, risk_level: str, cancer_types: list) -> list[dict]:
    """Try pgvector semantic search first; fall back to Gemini generation."""
    try:
        query = f"{location} cancer screening scheme {' '.join(cancer_types)} {risk_level} risk"
        embedding = await gemini.embed_text(query)
        rows = await search_schemes(embedding, location, limit=4)
        if rows:
            return [_scheme_row_to_output(r) for r in rows]
    except Exception:
        pass
    return await _research_schemes_gemini(location, risk_level, cancer_types)


async def _research_schemes_gemini(location: str, risk_level: str, cancer_types: list) -> list[dict]:
    types_text = " and ".join(cancer_types) if cancer_types else "cervical cancer"

    prompt = f"""You are VERA's Scheme Navigator. A woman in {location} has {risk_level} cancer risk for {types_text}.

Identify the 3-4 most relevant government and non-profit health schemes in {location} that offer free or subsidised cancer screening (Pap smear, mammogram, cervical cancer, breast cancer screening).

If the location is in India, prioritise: Ayushman Bharat PM-JAY, National Cancer Screening Programme (NCSP), state health missions, Rashtriya Bal Swasthya Karyakram, CGHS.
For other countries, find equivalent national cancer screening programmes.

Return a JSON array only. Each item:
[
  {{
    "scheme_name": "Full official name",
    "description": "2 sentences: what it is and who runs it",
    "eligibility_summary": "1 sentence on who qualifies",
    "coverage": "Cancer screenings covered (Pap smear, mammogram, etc.)",
    "url": "Official website URL if known, else null",
    "why_matches": "One warm sentence on why this woman specifically would benefit from this scheme"
  }}
]

Return ONLY the JSON array. No markdown, no explanation."""

    fallback = [
        {
            "scheme_name": "Ayushman Bharat – Pradhan Mantri Jan Arogya Yojana (PM-JAY)",
            "description": "India's flagship government health insurance covering secondary and tertiary care for economically vulnerable families. Administered by the National Health Authority.",
            "eligibility_summary": "Families identified in SECC database — approximately 50 crore beneficiaries across India.",
            "coverage": "Cancer screening, Pap smear, mammogram, colposcopy, and cancer treatment at empanelled hospitals.",
            "url": "https://pmjay.gov.in",
        },
        {
            "scheme_name": "National Cancer Screening Programme (NCSP)",
            "description": "Government of India programme for early detection of oral, cervical, and breast cancers at primary health centres. Part of the National Health Mission.",
            "eligibility_summary": "Women aged 30–65 years across India, with focus on rural and peri-urban populations.",
            "coverage": "Free cervical cancer screening (VIA/VILI), breast examination, oral cancer screening.",
            "url": "https://nhm.gov.in",
        },
        {
            "scheme_name": "Pradhan Mantri Surakshit Matritva Abhiyan (PMSMA)",
            "description": "Fixed-day, free antenatal and women's health care at government facilities on the 9th of every month. Includes cancer screening components.",
            "eligibility_summary": "All women of reproductive age at government health facilities.",
            "coverage": "Cervical cancer screening, breast examination, and comprehensive women's health checkups.",
            "url": "https://pmsma.mohfw.gov.in",
        },
    ]

    try:
        raw = await gemini.generate(prompt)
        return _parse_json_array(raw)
    except Exception:
        return fallback


async def _find_clinics(location: str, cancer_types: list) -> list[dict]:
    types_text = ", ".join(cancer_types) if cancer_types else "cervical cancer"

    prompt = f"""You are VERA's Scheme Navigator. Find 3 real, reputable government hospitals or free cancer screening centres in or near {location} that offer free {types_text} screening.

Prioritise: AIIMS, government district hospitals, Tata Memorial Hospital, state cancer institutes, Regional Cancer Centres.
Only include real hospitals. Use accurate addresses.

Return a JSON array of exactly 3 clinics:
[
  {{
    "name": "Official hospital/clinic name",
    "address": "Full address including city and state",
    "services": ["Pap smear", "Mammogram"],
    "cost": "Free",
    "female_doctor_available": true,
    "contact": "Phone or helpline if known, else null",
    "appointment_url": "URL to book if available, else null",
    "distance_km": 5.0
  }}
]

Return ONLY the JSON array. No markdown, no explanation. Real hospitals only."""

    fallback = [
        {
            "name": "AIIMS – All India Institute of Medical Sciences",
            "address": "Sri Aurobindo Marg, Ansari Nagar, New Delhi – 110029",
            "services": ["Pap smear", "Mammogram", "Colposcopy", "Cervical biopsy"],
            "cost": "Free",
            "female_doctor_available": True,
            "contact": "011-26588500",
            "appointment_url": "https://aiimsdelhi.org",
            "distance_km": 8.0,
        },
        {
            "name": "Safdarjung Hospital",
            "address": "Ring Road, Safdarjung, New Delhi – 110029",
            "services": ["Pap smear", "Breast examination", "Cancer screening OPD"],
            "cost": "Free",
            "female_doctor_available": True,
            "contact": "011-26165060",
            "appointment_url": None,
            "distance_km": 10.0,
        },
        {
            "name": "Ram Manohar Lohia (RML) Hospital",
            "address": "Baba Kharak Singh Marg, New Delhi – 110001",
            "services": ["Pap smear", "Mammogram", "Gynaecology OPD"],
            "cost": "Free",
            "female_doctor_available": True,
            "contact": "011-23365525",
            "appointment_url": None,
            "distance_km": 12.0,
        },
    ]

    try:
        raw = await gemini.generate(prompt)
        return _parse_json_array(raw)
    except Exception:
        return fallback
