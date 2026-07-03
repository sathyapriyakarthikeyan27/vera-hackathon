"""
Scheme Navigator Agent (Agent 2).

Serving priority for schemes:
  1. Grounded RAG over the real, licensed source corpus (source_documents /
     scheme_chunks / scheme_facts) for jurisdictions we have ingested. The LLM only
     explains retrieved, cited content and verified facts — it never invents schemes.
  2. Curated synthetic scheme_data (pgvector) for jurisdictions not yet ingested.
     This is human-written mock data, not LLM-generated, so it is safe to serve.
  3. Grounded-empty: an official directory handoff when we have neither. We never
     ask the LLM to fabricate scheme or clinic facts.

Clinics are NOT generated. We have no verified clinic corpus yet, so instead of
inventing hospital names/addresses/phone numbers (a patient-safety hazard) we hand the
user the official screening-service directory for their jurisdiction.
"""

from typing import Optional

from services.session_store import get_session, update_session
from services import gemini, rag_store
from . import prompts
from services.database import search_schemes, list_schemes_by_country
from services.ingestion.sources_uk import OGL_ATTRIBUTION
from services.ingestion.sources_india import GOI_ATTRIBUTION
from services.ingestion.sources_who import WHO_ATTRIBUTION


def _attribution_for(license: Optional[str]) -> Optional[str]:
    """Map a source's license tag to the attribution string shown to users."""
    lic = (license or "")
    if lic.startswith("OGL"):
        return OGL_ATTRIBUTION
    if lic.startswith("GoI"):
        return GOI_ATTRIBUTION
    if lic.startswith("CC-BY-NC-SA"):
        return WHO_ATTRIBUTION
    return None

_AGE_LABELS = {
    "under_25": "under 25", "25_34": "25 to 34", "35_44": "35 to 44",
    "45_54": "45 to 54", "55_plus": "over 55",
}

# Map a user's location (city or country string) to a screening jurisdiction. Kept
# small and explicit; extend as more jurisdictions are ingested. Matching is
# case-insensitive substring, country names first then major cities.
_JURISDICTION_MARKERS = {
    "UK": [
        "united kingdom", "uk", "england", "scotland", "wales", "northern ireland",
        "london", "manchester", "birmingham", "leeds", "glasgow", "liverpool",
        "edinburgh", "bristol", "sheffield", "cardiff", "belfast", "newcastle",
    ],
    "India": [
        "india", "delhi", "mumbai", "bengaluru", "bangalore", "hyderabad", "chennai",
        "kolkata", "pune", "ahmedabad", "jaipur", "lucknow", "surat",
    ],
    "Egypt": ["egypt", "cairo", "alexandria", "giza", "luxor", "aswan"],
}

# Official, real screening-service directories per jurisdiction. These are stable
# government entry points, not fabricated facilities — the grounded substitute for
# an invented hospital list.
_CARE_DIRECTORY = {
    "UK": {
        "label": "NHS: find screening and cancer services near you",
        "url": "https://www.nhs.uk/nhs-services/find-a-cancer-service/",
        "note": (
            "You can find your nearest NHS screening and cancer services here. "
            "Screening invitations also arrive automatically from your GP."
        ),
        "attribution": OGL_ATTRIBUTION,
    },
    "India": {
        "label": "National Health Mission: find a government health facility",
        "url": "https://nhm.gov.in",
        "note": (
            "Cancer screening is available at government primary health centres and "
            "district hospitals. Your nearest centre can guide your next step."
        ),
    },
    "Egypt": {
        "label": "Ministry of Health: 100 Million Seha screening services",
        "url": "https://www.mohp.gov.eg",
        "note": (
            "Free cancer screening is offered through government health units and the "
            "100 Million Seha initiative."
        ),
    },
}


def _jurisdiction_for_location(location: str) -> Optional[str]:
    loc = (location or "").lower()
    for jurisdiction, markers in _JURISDICTION_MARKERS.items():
        if any(m in loc for m in markers):
            return jurisdiction
    return None


def _parse_json_array(raw: str) -> list:
    """Parse and validate model output as a JSON array. Raises on anything else,
    so it doubles as the cache validator (bad values are never cached/served)."""
    data = gemini.parse_json(raw)
    if not isinstance(data, list):
        raise ValueError("expected a JSON array")
    return data


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
    jurisdiction = _jurisdiction_for_location(location)

    schemes_result = await _find_schemes(location, jurisdiction, risk_level, cancer_types, answers)

    output = {
        "matched_schemes": schemes_result,
        # No fabricated clinics. We surface the official directory instead until a
        # verified clinic corpus exists.
        "nearest_clinics": [],
        "care_directory": _care_directory(jurisdiction),
        "recommended_specialist": specialist,
    }

    completed = list(session.get("completed_agents") or [])
    if "scheme_navigator" not in completed:
        completed.append("scheme_navigator")

    await update_session(session_id, {"schemes_output": output, "completed_agents": completed})
    return output


def _care_directory(jurisdiction: Optional[str]) -> dict:
    """Official screening-service directory for the jurisdiction (real, not generated)."""
    if jurisdiction and jurisdiction in _CARE_DIRECTORY:
        return _CARE_DIRECTORY[jurisdiction]
    return {
        "label": "Find cancer screening services near you",
        "url": None,
        "note": (
            "I don't yet have verified screening services for your area. Your local "
            "doctor or government health service can point you to the nearest screening."
        ),
    }


async def _find_schemes(
    location: str, jurisdiction: Optional[str], risk_level: str,
    cancer_types: list, answers: dict,
) -> list[dict]:
    """
    Serving tiers, best first, never LLM-invented:
      1. National grounded RAG (real ingested sources for the user's country)
      2. Curated country data (human-written scheme_data)
      3. WHO GLOBAL grounded baseline (real, cited guidance for any country)
      4. Official-directory pointer
    """
    # 1. National grounded
    if jurisdiction and await rag_store.has_active_corpus(jurisdiction):
        grounded = await _grounded_schemes(jurisdiction, risk_level, cancer_types, answers)
        if grounded:
            return grounded

    # 2. Curated country data
    curated = await _curated_schemes(location, jurisdiction, risk_level, cancer_types)
    if curated:
        return curated

    # 3. WHO global baseline — so no user is left without real, cited guidance
    if await rag_store.has_active_corpus("GLOBAL"):
        baseline = await _grounded_schemes("GLOBAL", risk_level, cancer_types, answers)
        if baseline:
            return baseline

    # 4. Directory pointer
    return [_no_scheme_notice(jurisdiction)]


def _no_scheme_notice(jurisdiction: Optional[str]) -> dict:
    directory = _care_directory(jurisdiction)
    return {
        "scheme_name": "Finding schemes for your area",
        "description": (
            "I don't yet have verified government schemes for your location. I don't "
            "want to guess, so here is the official place to look."
        ),
        "eligibility_summary": directory["note"],
        "coverage": "",
        "url": directory.get("url"),
        "why_matches": "",
        "source": "directory",
    }


async def _curated_schemes(
    location: str, jurisdiction: Optional[str], risk_level: str, cancer_types: list
) -> list[dict]:
    """
    Curated synthetic scheme_data (human-written, not LLM-generated), retrieved by
    country via pgvector. Safe to serve for jurisdictions we have not yet ingested.
    Returns [] when nothing matches — never falls through to invented schemes.
    """
    country = jurisdiction or location
    rows: list[dict] = []
    try:
        query = f"{country} cancer screening scheme {' '.join(cancer_types)} {risk_level} risk"
        embedding = await gemini.embed_text_cached(query)
        rows = await search_schemes(embedding, country, limit=4)
    except Exception:
        rows = []
    # Fallback for rows without embeddings (legacy seed): plain country lookup.
    if not rows:
        try:
            rows = await list_schemes_by_country(country, limit=4)
        except Exception:
            rows = []
    return [dict(_scheme_row_to_output(r), source="curated") for r in rows]


# ── Grounded RAG (real-source corpus) ────────────────────────────────────────

def _scheme_query(risk_level: str, cancer_types: list) -> str:
    types = " ".join(cancer_types) if cancer_types else "cancer"
    return (
        f"government cancer screening programme for {types}: who is eligible, "
        f"what age, how often, cost, and how to access it ({risk_level} risk)"
    )


def _context_block(chunks: list[dict], facts: list[dict]) -> str:
    """Build the grounding context the LLM is allowed to use — nothing else."""
    lines = ["SOURCE PASSAGES (the only facts you may use):"]
    for i, c in enumerate(chunks, 1):
        head = f" — {c['heading']}" if c.get("heading") else ""
        lines.append(f"[{i}] ({c['publisher']}, {c['url']}){head}\n{c['content']}")
    if facts:
        lines.append("\nVERIFIED STRUCTURED FACTS (clinician-approved):")
        for f in facts:
            age = ""
            if f.get("eligible_age_min") or f.get("eligible_age_max"):
                age = f" ages {f.get('eligible_age_min','?')} to {f.get('eligible_age_max','?')}"
            interval = f" every {f['interval_months']} months" if f.get("interval_months") else ""
            cost = f", {f['cost']}" if f.get("cost") else ""
            lines.append(
                f"- {f['programme']} ({f['cancer_type']}):{age}{interval}{cost}. "
                f"Method: {f.get('method') or 'n/a'}."
            )
    return "\n\n".join(lines)


async def _grounded_schemes(
    jurisdiction: str, risk_level: str, cancer_types: list, answers: dict
) -> list[dict]:
    """
    Grounded generation over the real-source corpus. The LLM only rephrases retrieved,
    cited passages and verified facts. URLs are validated against the retrieved sources
    so no link can be invented. Returns [] if retrieval finds nothing (caller degrades).
    """
    types = [t.lower() for t in cancer_types] if cancer_types else None
    query = _scheme_query(risk_level, cancer_types)
    try:
        embedding = await gemini.embed_query(query)
        chunks = await rag_store.hybrid_search(embedding, query, jurisdiction, types, limit=6)
    except Exception:
        chunks = []
    if not chunks:
        return []

    facts: list[dict] = []
    for ct in (cancer_types or []):
        facts.extend(await rag_store.get_verified_facts(jurisdiction, ct.lower()))

    # Provenance we can trust: the set of source URLs actually retrieved.
    source_urls = {c["url"] for c in chunks if c.get("url")}
    # A representative source for stamping publisher / last_verified / attribution.
    top = chunks[0]
    provenance = {
        "publisher": top.get("publisher"),
        "last_verified": top["last_verified"].date().isoformat() if top.get("last_verified") else None,
        "attribution": _attribution_for(top.get("license")),
    }

    person = _build_person_description(answers, risk_level, cancer_types)
    prompt = prompts.grounded_schemes_prompt(person, _context_block(chunks, facts))

    # The prompt version is part of the key so a prompt change never serves
    # generations cached under the old prompt.
    cache_key = (
        f"grounded_schemes:{prompts.GROUNDED_SCHEMES_PROMPT_VERSION}:"
        f"{jurisdiction}:{risk_level}:{'+'.join(sorted(cancer_types))}"
    )
    try:
        raw = await gemini.generate_cached(
            prompt, cache_key, validate=_parse_json_array, json_mode=True
        )
        parsed = _parse_json_array(raw)
    except Exception:
        parsed = []

    if not parsed:
        return _deterministic_schemes(chunks, facts, provenance)

    out = []
    for s in parsed:
        if not isinstance(s, dict) or not s.get("scheme_name"):
            continue
        # Guard against a hallucinated URL: keep it only if it was a retrieved source.
        url = s.get("url") if s.get("url") in source_urls else top.get("url")
        out.append({
            "scheme_name": s.get("scheme_name"),
            "description": s.get("description", ""),
            "eligibility_summary": s.get("eligibility_summary", ""),
            "coverage": s.get("coverage", ""),
            "url": url,
            "why_matches": s.get("why_matches", ""),
            "source": "grounded",
            "publisher": provenance["publisher"],
            "last_verified": provenance["last_verified"],
            "attribution": provenance["attribution"],
        })
    return out or _deterministic_schemes(chunks, facts, provenance)


def _deterministic_schemes(chunks: list[dict], facts: list[dict], provenance: dict) -> list[dict]:
    """
    LLM-free grounded output built directly from verified facts (preferred) or the top
    retrieved passage. Guarantees we still return real, cited content if generation fails.
    """
    if facts:
        out = []
        for f in facts[:3]:
            age = ""
            if f.get("eligible_age_min") or f.get("eligible_age_max"):
                age = f"ages {f.get('eligible_age_min','?')} to {f.get('eligible_age_max','?')}"
            interval = f", every {f['interval_months'] // 12} years" if f.get("interval_months") else ""
            out.append({
                "scheme_name": f["programme"],
                "description": f"{f['programme']} offers {f.get('method') or 'screening'}.",
                "eligibility_summary": f"{age}{interval}. {f.get('cost') or ''}".strip(", ").strip(),
                "coverage": f.get("cancer_type", ""),
                "url": f.get("source_url"),
                "why_matches": "",
                "source": "grounded_facts",
                "publisher": provenance["publisher"],
                "last_verified": provenance["last_verified"],
                "attribution": provenance["attribution"],
            })
        return out
    c = chunks[0]
    return [{
        "scheme_name": c.get("title") or "Screening programme",
        "description": c["content"][:280],
        "eligibility_summary": "See the official source for full eligibility.",
        "coverage": "",
        "url": c.get("url"),
        "why_matches": "",
        "source": "grounded_passage",
        "publisher": provenance["publisher"],
        "last_verified": provenance["last_verified"],
        "attribution": provenance["attribution"],
    }]
