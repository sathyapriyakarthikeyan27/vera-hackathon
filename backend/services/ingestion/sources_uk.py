"""
UK source registry — the vetted, licensed inputs to the RAG corpus.

Every URL here was resolved from the live NHS screening hub
(https://www.nhs.uk/tests-and-treatments/nhs-screening/) rather than assumed, because
NHS restructures its paths (the old /conditions/cervical-screening now lives at
/tests-and-treatments/cervical-screening/). The fetcher follows redirects and records
the final resolved URL, so a future move is caught by the freshness re-crawl rather
than silently serving a 404.

License: NHS England / UKHSA content on nhs.uk and gov.uk is published under the
Open Government Licence v3.0 (OGL-v3.0), which permits reuse with attribution:
"Contains public sector information licensed under the Open Government Licence v3.0."
Only add a source here if its license permits reuse — this is the licensing gate.

We start with UK deliberately: cleanest HTML, permissive license, English, and the
three programmes map onto VERA's existing cancer types.
"""

# OGL v3.0 attribution string to surface alongside any UK content in the UI.
OGL_ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0."
)

UK_SOURCES: list[dict] = [
    {
        "source_key": "uk_nhs_cervical_screening",
        "title": "NHS Cervical Screening",
        "url": "https://www.nhs.uk/tests-and-treatments/cervical-screening/",
        "jurisdiction": "UK",
        "source_type": "html",
        "publisher": "NHS",
        "license": "OGL-v3.0",
        "cancer_types": ["cervical"],
        "programme": "NHS Cervical Screening Programme",
    },
    {
        "source_key": "uk_nhs_breast_screening",
        "title": "NHS Breast Screening",
        "url": "https://www.nhs.uk/conditions/breast-cancer-screening/",
        "jurisdiction": "UK",
        "source_type": "html",
        "publisher": "NHS",
        "license": "OGL-v3.0",
        "cancer_types": ["breast"],
        "programme": "NHS Breast Screening Programme",
    },
    {
        "source_key": "uk_nhs_bowel_screening",
        "title": "NHS Bowel Cancer Screening",
        "url": "https://www.nhs.uk/tests-and-treatments/bowel-cancer-screening/",
        "jurisdiction": "UK",
        "source_type": "html",
        "publisher": "NHS",
        "license": "OGL-v3.0",
        "cancer_types": ["colorectal"],
        "programme": "NHS Bowel Cancer Screening Programme",
    },
    {
        "source_key": "uk_nhs_screening_hub",
        "title": "NHS Screening (overview)",
        "url": "https://www.nhs.uk/tests-and-treatments/nhs-screening/",
        "jurisdiction": "UK",
        "source_type": "html",
        "publisher": "NHS",
        "license": "OGL-v3.0",
        "cancer_types": ["cervical", "breast", "colorectal"],
        "programme": "NHS Screening Programmes",
    },
]
