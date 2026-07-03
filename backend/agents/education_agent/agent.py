"""
Education Agent.
Uses Gemini to generate personalised plain-language cancer education content:
a warm intro, 4 topic sections, and a concise summary — in the user's language.
"""

import asyncio
import json
from typing import Optional

from services.session_store import get_session, update_session
from services import gemini
from . import prompts

_SCREENING_NAME = {
    "cervical": "Pap smear (cervical screening)",
    "breast": "mammogram (breast screening)",
    "ovarian": "pelvic ultrasound (ovarian screening)",
}

_LANG_NAME = {"en": "English", "hi": "Hindi", "ta": "Tamil"}

_FALLBACK_SECTIONS = [
    {
        "title": "What is cervical cancer?",
        "content": (
            "Cervical cancer develops in the cells lining the cervix, the lower part of the uterus. "
            "It is one of the most preventable cancers when caught early through regular screening. "
            "Most cases are linked to the Human Papillomavirus (HPV), a very common infection."
        ),
    },
    {
        "title": "What does a Pap smear involve?",
        "content": (
            "A Pap smear is a quick, simple test done at a clinic. A doctor gently collects a small "
            "sample of cells from your cervix using a soft brush. It takes about 5 minutes. "
            "Many women feel mild discomfort but no real pain, and it is over very quickly."
        ),
    },
    {
        "title": "What to expect on the day",
        "content": (
            "Wear comfortable clothing and arrive a few minutes early to fill in a short form. "
            "You will be asked to lie on an examination table for the sample collection. "
            "Bring a trusted friend or family member for support if that helps you feel at ease."
        ),
    },
    {
        "title": "After your screening",
        "content": (
            "Results usually arrive within 2–4 weeks by phone or letter. "
            "A normal result means no abnormal cells were found. Great news. "
            "If the result is unclear or shows changes, a doctor will explain the next steps calmly and clearly."
        ),
    },
]


async def generate(session_id: str) -> Optional[dict]:
    session = await get_session(session_id)
    if not session:
        return None

    if session.get("education_output"):
        return session["education_output"]

    risk_profile = session.get("risk_profile") or {}
    risk_level: str = risk_profile.get("risk_level", "Moderate")
    cancer_types: list = risk_profile.get("cancer_types_flagged") or ["cervical"]
    user_name: str = session.get("user_name") or ""
    language: str = session.get("language") or "en"
    primary_cancer: str = cancer_types[0] if cancer_types else "cervical"

    intro, sections = await asyncio.gather(
        _generate_intro(user_name, risk_level, primary_cancer, language),
        _generate_sections(primary_cancer, language),
    )

    summary = sections[0]["content"] if sections else _FALLBACK_SECTIONS[0]["content"]

    output = {
        "personalized_intro": intro,
        "text_summary": summary,
        "language": language,
        "cancer_type": primary_cancer,
        "video_url": None,
        "sections": sections,
    }

    completed = list(session.get("completed_agents") or [])
    if "education_agent" not in completed:
        completed.append("education_agent")

    await update_session(session_id, {"education_output": output, "completed_agents": completed})
    return output


async def _generate_intro(
    user_name: str, risk_level: str, cancer_type: str, language: str
) -> str:
    lang = _LANG_NAME.get(language, "English")
    name_clause = f"Their name is {user_name}." if user_name else ""

    prompt = prompts.intro_prompt(name_clause, risk_level, cancer_type, lang)

    fallback = (
        f"Understanding {cancer_type} cancer is one of the most important steps you can take for your health. "
        "Here is everything you need to know, in plain language, at your own pace."
    )

    return await gemini.generate_safe(prompt, fallback=fallback)


async def _generate_sections(cancer_type: str, language: str) -> list[dict]:
    lang = _LANG_NAME.get(language, "English")
    screening = _SCREENING_NAME.get(cancer_type, f"{cancer_type} cancer screening")

    prompt = prompts.sections_prompt(cancer_type, screening, lang)

    try:
        raw = await gemini.generate_json(prompt, temperature=0.4)
        sections = gemini.parse_json(raw)
        return sections if isinstance(sections, list) else _FALLBACK_SECTIONS
    except Exception:
        return _FALLBACK_SECTIONS
