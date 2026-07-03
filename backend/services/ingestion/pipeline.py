"""
Ingestion orchestrator: fetch -> chunk -> embed -> stage facts, with change detection.

The core policy — the whole reason this pipeline exists — is the split between:

  * Narrative chunks (scheme_chunks): explanatory prose. Retrieval-grounded and always
    surfaced with provenance + a "verified as of" date, so refreshing them
    automatically on change is low-harm. They are re-embedded whenever content changes.

  * Structured facts (scheme_facts): the eligibility ages, intervals and costs a wrong
    answer could actually harm someone with. These are ALWAYS staged as verified = FALSE.
    Nothing in this module publishes them. A human flips verified = TRUE
    (rag_store.mark_fact_verified) after review. That is the safety gate.

Change detection compares the freshly fetched content_hash to the stored one:
  * first ingest        -> write chunks, stage facts, status 'active'
  * unchanged           -> touch last_fetched/last_verified, status stays 'active'
  * changed (re-crawl)  -> refresh chunks, re-stage facts unverified, status
                           'pending_review' so a human is alerted before it ships
  * fetch/parse error   -> status 'error', last_error recorded, corpus left intact
"""

import json
import logging
import os

from services import gemini, rag_store
from services.ingestion.chunker import chunk_sections
from services.ingestion.fetcher import fetch_source

logger = logging.getLogger(__name__)

# Model for the first-pass fact extraction. Defaults to Pro for accuracy on the
# safety-critical numbers; override to Flash (FACT_EXTRACTION_MODEL=gemini-2.5-flash)
# where Pro quota is constrained — a human reviews every fact regardless.
_FACT_MODEL = os.getenv("FACT_EXTRACTION_MODEL", gemini.GEMINI_PRO)


def _parse_json_array(raw: str) -> list:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


async def _extract_facts(meta: dict, full_text: str, source_url: str, content_hash: str) -> list[dict]:
    """
    Use Gemini to pull the safety-critical structured facts out of the source text.
    Output is staged UNVERIFIED — this is a first-pass extraction for a human to check,
    not a source of truth. Returns [] on any failure (facts are optional; chunks aren't).
    """
    prompt = f"""You are extracting structured cancer-screening facts from official {meta['jurisdiction']} health content.

Programme: {meta.get('programme', meta['title'])}
Cancer type(s): {', '.join(meta['cancer_types'])}

From the text below, extract each distinct screening offer as a JSON object. Only state
facts explicitly present in the text. If a value is not stated, use null — never guess.

Return a JSON array only, no markdown:
[
  {{
    "programme": "official programme name",
    "cancer_type": "cervical | breast | colorectal | ...",
    "sex": "female | male | all",
    "eligible_age_min": integer or null,
    "eligible_age_max": integer or null,
    "interval_months": integer or null,
    "cost": "free | ... or null",
    "method": "short description of the test, or null",
    "notes": "one short sentence of important caveats, or null"
  }}
]

TEXT:
{full_text[:12000]}

Return ONLY the JSON array."""
    try:
        raw = await gemini.generate(prompt, _FACT_MODEL)
    except Exception as exc:
        logger.warning("Fact extraction failed for %s: %s", meta["source_key"], type(exc).__name__)
        return []

    facts = []
    for f in _parse_json_array(raw):
        if not isinstance(f, dict):
            continue
        facts.append({
            "jurisdiction": meta["jurisdiction"],
            "programme": f.get("programme") or meta.get("programme") or meta["title"],
            "cancer_type": (f.get("cancer_type") or (meta["cancer_types"] or ["unknown"])[0]),
            "sex": f.get("sex") or "all",
            "eligible_age_min": f.get("eligible_age_min"),
            "eligible_age_max": f.get("eligible_age_max"),
            "interval_months": f.get("interval_months"),
            "cost": f.get("cost"),
            "method": f.get("method"),
            "notes": f.get("notes"),
            "source_url": source_url,
            "content_hash": content_hash,
        })
    return facts


async def _embed_chunks(chunks) -> list[dict]:
    embedded = []
    for c in chunks:
        # Prepend the heading so the embedding carries section context.
        payload = f"{c.heading}\n{c.content}".strip() if c.heading else c.content
        embedding = await gemini.embed_document(payload)
        embedded.append({
            "heading": c.heading or None,
            "content": c.content,
            "token_estimate": c.token_estimate,
            "embedding": embedding,
        })
    return embedded


async def ingest_source(meta: dict, *, force: bool = False) -> dict:
    """
    Ingest (or re-verify) a single source. `meta` is one entry from a source registry
    (e.g. sources_uk.UK_SOURCES). `force=True` re-embeds even if content is unchanged.
    Returns a summary dict; never raises (failures are recorded on the source row).
    """
    source_id = await rag_store.upsert_source(
        source_key=meta["source_key"],
        title=meta["title"],
        url=meta["url"],
        jurisdiction=meta["jurisdiction"],
        source_type=meta["source_type"],
        publisher=meta["publisher"],
        license=meta["license"],
        cancer_types=meta["cancer_types"],
    )
    existing = await rag_store.get_source_by_key(meta["source_key"])
    prior_hash = existing.get("content_hash") if existing else None

    try:
        result = await fetch_source(
            meta["url"], meta["source_type"], render=bool(meta.get("render")),
        )
    except Exception as exc:
        logger.warning("Fetch failed for %s: %s", meta["source_key"], exc)
        await rag_store.set_source_status(source_id, "error", str(exc)[:500])
        return {"source_key": meta["source_key"], "status": "error", "error": str(exc)[:200]}

    changed = result.content_hash != prior_hash

    # Unchanged and already ingested: cheap re-verification, no re-embed.
    if prior_hash and not changed and not force:
        await rag_store.mark_source_fetched(source_id, result.content_hash, result.published_date)
        await rag_store.mark_source_verified(source_id)
        n = await rag_store.count_chunks(source_id)
        logger.info("Re-verified (unchanged): %s (%d chunks)", meta["source_key"], n)
        return {"source_key": meta["source_key"], "status": "unchanged", "chunks": n}

    # First ingest, real change, or forced: refresh the corpus.
    try:
        chunks = chunk_sections(result.sections)
        embedded = await _embed_chunks(chunks)
        n = await rag_store.replace_chunks(source_id, embedded)
        facts = await _extract_facts(meta, result.full_text, result.final_url, result.content_hash)
        n_facts = await rag_store.stage_facts(source_id, facts)
    except Exception as exc:
        logger.warning("Embed/store failed for %s: %s", meta["source_key"], exc)
        await rag_store.set_source_status(source_id, "error", str(exc)[:500])
        return {"source_key": meta["source_key"], "status": "error", "error": str(exc)[:200]}

    await rag_store.mark_source_fetched(source_id, result.content_hash, result.published_date)

    if prior_hash and changed:
        # A previously-ingested source changed. Chunks are refreshed, but a human must
        # confirm before we treat it as current — this is the freshness gate.
        await rag_store.set_source_status(
            source_id, "pending_review", "content changed on re-crawl; needs human review"
        )
        status = "changed"
        logger.info("CHANGED (needs review): %s — %d chunks, %d facts staged",
                    meta["source_key"], n, n_facts)
    else:
        await rag_store.mark_source_verified(source_id)  # sets status 'active'
        status = "ingested"
        logger.info("Ingested: %s — %d chunks, %d facts staged (pending review)",
                    meta["source_key"], n, n_facts)

    return {
        "source_key": meta["source_key"],
        "status": status,
        "final_url": result.final_url,
        "chunks": n,
        "facts_staged": n_facts,
    }


async def ingest_registry(sources: list[dict], *, force: bool = False) -> list[dict]:
    """Ingest a whole registry. Ensures the HNSW index exists first."""
    await rag_store.ensure_rag_indexes()
    results = []
    for meta in sources:
        results.append(await ingest_source(meta, force=force))
    return results
