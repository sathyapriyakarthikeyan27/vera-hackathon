"""
Single place that knows every jurisdiction's source registry.

Add a jurisdiction by importing its sources_*.py list here. The ingestion CLI and the
scheduled re-verification task both read from this, so they stay in sync automatically.
"""

from services.ingestion.sources_uk import UK_SOURCES
from services.ingestion.sources_india import INDIA_SOURCES
from services.ingestion.sources_who import WHO_SOURCES

REGISTRIES: dict[str, list[dict]] = {
    "UK": UK_SOURCES,
    "India": INDIA_SOURCES,
    "GLOBAL": WHO_SOURCES,  # WHO baseline — fallback for un-ingested jurisdictions
}


def all_sources() -> list[dict]:
    """Every source across every jurisdiction, in a stable order."""
    out: list[dict] = []
    for jurisdiction in sorted(REGISTRIES):
        out.extend(REGISTRIES[jurisdiction])
    return out


def sources_for(jurisdiction: str) -> list[dict]:
    """Sources for one jurisdiction (case-insensitive), or [] if unknown."""
    for key, sources in REGISTRIES.items():
        if key.lower() == jurisdiction.lower():
            return sources
    return []
