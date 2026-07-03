"""
India source registry — real NP-NCD / NHM cancer-screening content.

Every URL here was validated through the pipeline's own fetcher (fetch + extract
succeeds) rather than assumed. India's population-based screening programme (NP-NCD,
formerly NPCDCS) covers oral, breast, and cervical cancer for adults aged 30+, so
these sources map onto VERA's cancer types.

Sources deliberately excluded after validation:
  * mohfw.gov.in PDFs — the server returns 403 to non-browser clients (bot-blocked).
  * nha.gov.in / PM-JAY pages — JS-rendered SPA with no server-side text, and the
    HBP benefit-package PDFs are gated (do not serve a valid PDF to a direct GET).
    A PM-JAY / HBP loader needs a browser-rendering fetch or a manually obtained file;
    see docs. It is NOT included here rather than shipping a source that 404s silently.

Licensing note (IMPORTANT — differs from UK): Government of India website content is
GoI copyright, not a blanket open licence like the UK's OGL. VERA surfaces short factual
summaries with attribution and a link back to the source, which is defensible for factual
public-health information, but a formal licensing review is a production prerequisite
before any commercial reuse. license is tagged "GoI-review" to make that explicit.
"""

# Attribution surfaced alongside any Indian government content in the UI.
GOI_ATTRIBUTION = (
    "Source: National Health Mission, Ministry of Health and Family Welfare, "
    "Government of India."
)

INDIA_SOURCES: list[dict] = [
    {
        "source_key": "in_nhm_npcdcs_overview",
        "title": "National Programme for Prevention and Control of Cancer, Diabetes, CVD and Stroke (NP-NCD)",
        "url": "https://nhm.gov.in/index1.php?lang=1&level=2&sublinkid=1048&lid=604",
        "jurisdiction": "India",
        "source_type": "html",
        "publisher": "National Health Mission (MoHFW)",
        "license": "GoI-review",
        "cancer_types": ["oral", "breast", "cervical"],
        "programme": "National Programme for Prevention and Control of NCDs (NP-NCD)",
    },
    {
        "source_key": "in_nhm_ncd_operational_guidelines",
        "title": "Operational Guidelines: Prevention, Screening and Control of Common NCDs",
        "url": "https://nhm.gov.in/images/pdf/NHM/NHM-Guidelines/Operational_Guidelines_NCDs.pdf",
        "jurisdiction": "India",
        "source_type": "pdf",
        "publisher": "National Health Mission (MoHFW)",
        "license": "GoI-review",
        "cancer_types": ["oral", "breast", "cervical"],
        "programme": "Population Based Screening (NP-NCD)",
    },
    {
        "source_key": "in_nhm_ncd_training_modules",
        "title": "Training Modules for Programme Managers: Prevention and Screening of Common NCDs",
        "url": "https://nhm.gov.in/New-Update-2025-26/Whats-new/Training-Modules-NCDs.pdf",
        "jurisdiction": "India",
        "source_type": "pdf",
        "publisher": "National Health Mission (MoHFW)",
        "license": "GoI-review",
        "cancer_types": ["oral", "breast", "cervical"],
        "programme": "Population Based Screening (NP-NCD)",
    },
]

# PM-JAY (nha.gov.in) was evaluated with the Playwright render path and dropped: the SPA
# loads a ~600KB JS bundle but renders ZERO visible text at /PM-JAY even in a real headless
# Chromium (it detects headless and/or serves content only via deep in-app navigation). The
# render path itself is proven working on cooperative SPAs — this source is simply not
# viably ingestable without bespoke portal automation or a manually obtained HBP file.
# Add a "render": "browser" entry here once a cooperative PM-JAY content route is found.
