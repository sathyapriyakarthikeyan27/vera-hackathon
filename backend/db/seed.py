"""
Seed scheme_data table with mock government scheme + clinic data for pgvector RAG.
Called at startup only if the table is empty.
Embeddings generated via Gemini text-embedding-004 (768-dimensional).
"""

import asyncio
import logging
import os
from typing import Optional

import google.generativeai as genai

from services.database import count_schemes, insert_scheme

logger = logging.getLogger(__name__)

_SCHEMES = [
    # ── India ────────────────────────────────────────────────────────────────────
    {
        "scheme_name": "Ayushman Bharat – PM-JAY",
        "country": "India",
        "cancer_types": ["cervical", "breast", "colorectal", "oral"],
        "content": (
            "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY) is India's national "
            "health insurance scheme covering secondary and tertiary cancer care for "
            "economically vulnerable families. Covers Pap smear, mammogram, colposcopy, "
            "biopsy, and cancer treatment at empanelled hospitals at no cost. "
            "Approximately 50 crore beneficiaries across India."
        ),
        "metadata": {
            "eligibility": "Families in SECC database — bottom 40% by income",
            "coverage": "Cervical, breast, oral, colorectal cancer screening and treatment",
            "url": "https://pmjay.gov.in",
        },
    },
    {
        "scheme_name": "National Cancer Screening Programme (NCSP)",
        "country": "India",
        "cancer_types": ["cervical", "breast", "oral"],
        "content": (
            "The National Cancer Screening Programme (NCSP) under the National Health Mission "
            "provides free cancer screening for oral, cervical, and breast cancers at primary "
            "health centres across India. Available to women aged 30–65 at government facilities. "
            "Cervical screening uses VIA/VILI method, no referral required."
        ),
        "metadata": {
            "eligibility": "Women aged 30–65 across India",
            "coverage": "Free cervical VIA/VILI, breast examination, oral cancer screening",
            "url": "https://nhm.gov.in",
        },
    },
    {
        "scheme_name": "Pradhan Mantri Surakshit Matritva Abhiyan (PMSMA)",
        "country": "India",
        "cancer_types": ["cervical", "breast"],
        "content": (
            "PMSMA provides fixed-day free comprehensive women's health care including cancer "
            "screening on the 9th of every month at government facilities. Female doctors available. "
            "Covers cervical cancer screening, breast examination, and gynaecological check-ups "
            "for all women of reproductive age."
        ),
        "metadata": {
            "eligibility": "All women of reproductive age at government health facilities",
            "coverage": "Cervical and breast cancer screening, monthly camp format",
            "url": "https://pmsma.mohfw.gov.in",
        },
    },
    {
        "scheme_name": "Rashtriya Arogya Nidhi (RAN)",
        "country": "India",
        "cancer_types": ["cervical", "breast", "colorectal", "ovarian"],
        "content": (
            "Rashtriya Arogya Nidhi provides financial assistance to poor patients suffering "
            "from life-threatening diseases including cancer for treatment at government super-specialty "
            "hospitals. Covers diagnostic tests, biopsy, and cancer treatment for BPL families. "
            "Available at AIIMS and other central government hospitals."
        ),
        "metadata": {
            "eligibility": "BPL families requiring treatment at central government hospitals",
            "coverage": "Cancer diagnostics, biopsy, treatment including surgery",
            "url": "https://mohfw.gov.in",
        },
    },
    # ── Egypt ─────────────────────────────────────────────────────────────────────
    {
        "scheme_name": "National Health Insurance Authority (NHIA)",
        "country": "Egypt",
        "cancer_types": ["cervical", "breast", "colorectal"],
        "content": (
            "Egypt's National Health Insurance Authority (NHIA) provides universal health "
            "coverage including cancer screening and treatment. The 100 Million Health programme "
            "under NHIA offers free cancer screening for all Egyptian women including Pap smear, "
            "breast examination, and HPV testing at government health units nationwide."
        ),
        "metadata": {
            "eligibility": "All Egyptian nationals — universal coverage",
            "coverage": "Free cancer screening, Pap smear, mammogram at NHIA facilities",
            "url": "https://nhia.gov.eg",
        },
    },
    {
        "scheme_name": "100 Million Health Initiative – Cancer Screening",
        "country": "Egypt",
        "cancer_types": ["cervical", "breast", "liver"],
        "content": (
            "Egypt's 100 Million Health Initiative includes comprehensive cancer screening as "
            "part of the national health programme. Mobile screening units visit villages and "
            "underserved areas for breast and cervical cancer detection. Free for all women, "
            "especially targeting rural and peri-urban communities."
        ),
        "metadata": {
            "eligibility": "All women, prioritising rural areas",
            "coverage": "Free mobile cancer screening camps — cervical, breast",
            "url": "https://100million.mohp.gov.eg",
        },
    },
    # ── UK ────────────────────────────────────────────────────────────────────────
    {
        "scheme_name": "NHS Cervical Screening Programme",
        "country": "UK",
        "cancer_types": ["cervical"],
        "content": (
            "The NHS Cervical Screening Programme invites women and people with a cervix aged "
            "25–64 for free cervical screening (smear test / HPV test) every 3–5 years. "
            "Fully funded by NHS, no cost to the patient. Results within 2 weeks. "
            "Available at all GP surgeries across England, Scotland, Wales, and Northern Ireland."
        ),
        "metadata": {
            "eligibility": "Women aged 25–64 registered with a GP in the UK",
            "coverage": "Free HPV test and cervical screening every 3–5 years",
            "url": "https://www.nhs.uk/conditions/cervical-screening",
        },
    },
    {
        "scheme_name": "NHS Breast Screening Programme",
        "country": "UK",
        "cancer_types": ["breast"],
        "content": (
            "The NHS Breast Screening Programme invites women aged 50–70 for free mammograms "
            "every 3 years. Women outside this range can self-refer. Fully NHS-funded with "
            "no waiting list charges. Mobile screening units available in rural areas. "
            "Results typically within 2 weeks of the appointment."
        ),
        "metadata": {
            "eligibility": "Women aged 50–70 registered with NHS; self-referral available",
            "coverage": "Free mammogram every 3 years, extended screening available",
            "url": "https://www.nhs.uk/conditions/breast-screening-mammogram",
        },
    },
    {
        "scheme_name": "NHS Bowel Cancer Screening Programme",
        "country": "UK",
        "cancer_types": ["colorectal"],
        "content": (
            "The NHS Bowel Cancer Screening Programme provides free home testing kits (FIT test) "
            "to adults aged 50–74 every 2 years. Colonoscopy offered free to those with positive "
            "results. Fully NHS-funded. Proven to detect bowel cancer early when treatment is "
            "most effective. Available across all four nations of the UK."
        ),
        "metadata": {
            "eligibility": "Adults aged 50–74 registered with a GP in the UK",
            "coverage": "Free FIT home test kit, followed by free colonoscopy if positive",
            "url": "https://www.nhs.uk/conditions/bowel-cancer-screening",
        },
    },
]


async def _embed(text: str) -> Optional[list]:
    try:
        if not os.getenv("GEMINI_API_KEY"):
            return None
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        result = await asyncio.to_thread(
            genai.embed_content,
            model="models/text-embedding-004",
            content=text,
        )
        return result["embedding"]
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return None


async def seed_scheme_data() -> None:
    """Insert scheme data into pgvector if the table is empty."""
    try:
        count = await count_schemes()
        if count > 0:
            logger.info("scheme_data already seeded (%d rows) — skipping", count)
            return

        logger.info("Seeding %d schemes into pgvector…", len(_SCHEMES))
        for s in _SCHEMES:
            embedding = await _embed(s["content"])
            await insert_scheme(
                scheme_name=s["scheme_name"],
                country=s["country"],
                cancer_types=s["cancer_types"],
                content=s["content"],
                metadata=s["metadata"],
                embedding=embedding,
            )
        logger.info("Scheme data seeded successfully")
    except Exception as exc:
        logger.warning("Scheme seeding failed (non-fatal): %s", exc)
