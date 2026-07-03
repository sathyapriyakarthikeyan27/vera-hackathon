"""
WHO global baseline — jurisdiction "GLOBAL".

These are the World Health Organization cancer fact sheets: authoritative, English,
and applicable to every country. They are the floor of coverage so that a user in a
country we have not ingested nationally (say Brazil or Nigeria) still gets real, cited
screening guidance instead of nothing. National corpora (UK, India, ...) take priority;
GLOBAL is only reached as a fallback (see agent._find_schemes).

Every URL was validated through the pipeline's fetcher.

Licensing note: WHO content is published under CC BY-NC-SA 3.0 IGO — reuse permitted
with attribution, but **non-commercial**. That NC clause is a real constraint for a
commercial deployment and must be reviewed. license is tagged "CC-BY-NC-SA-3.0-IGO".
"""

WHO_ATTRIBUTION = (
    "© World Health Organization. Reproduced with attribution under "
    "CC BY-NC-SA 3.0 IGO."
)

WHO_SOURCES: list[dict] = [
    {
        "source_key": "who_fs_cervical_cancer",
        "title": "WHO Fact Sheet: Cervical Cancer",
        "url": "https://www.who.int/news-room/fact-sheets/detail/cervical-cancer",
        "jurisdiction": "GLOBAL",
        "source_type": "html",
        "publisher": "World Health Organization",
        "license": "CC-BY-NC-SA-3.0-IGO",
        "cancer_types": ["cervical"],
        "programme": "WHO cervical cancer screening guidance",
    },
    {
        "source_key": "who_fs_breast_cancer",
        "title": "WHO Fact Sheet: Breast Cancer",
        "url": "https://www.who.int/news-room/fact-sheets/detail/breast-cancer",
        "jurisdiction": "GLOBAL",
        "source_type": "html",
        "publisher": "World Health Organization",
        "license": "CC-BY-NC-SA-3.0-IGO",
        "cancer_types": ["breast"],
        "programme": "WHO breast cancer screening guidance",
    },
    {
        "source_key": "who_fs_colorectal_cancer",
        "title": "WHO Fact Sheet: Colorectal Cancer",
        "url": "https://www.who.int/news-room/fact-sheets/detail/colorectal-cancer",
        "jurisdiction": "GLOBAL",
        "source_type": "html",
        "publisher": "World Health Organization",
        "license": "CC-BY-NC-SA-3.0-IGO",
        "cancer_types": ["colorectal"],
        "programme": "WHO colorectal cancer screening guidance",
    },
    {
        "source_key": "who_fs_cancer_overview",
        "title": "WHO Fact Sheet: Cancer",
        "url": "https://www.who.int/news-room/fact-sheets/detail/cancer",
        "jurisdiction": "GLOBAL",
        "source_type": "html",
        "publisher": "World Health Organization",
        "license": "CC-BY-NC-SA-3.0-IGO",
        "cancer_types": ["cervical", "breast", "colorectal", "oral", "lung"],
        "programme": "WHO cancer prevention and early detection",
    },
]
