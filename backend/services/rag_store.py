"""
Data-access layer for the Agent 2 RAG corpus (source_documents / scheme_chunks /
scheme_facts). Kept separate from services/database.py so the RAG concern stays
cohesive.

Design notes:
- Chunks are replaced atomically per source (delete-then-insert in a transaction),
  so re-ingesting a source never leaves a half-updated corpus.
- Facts are always staged as verified = FALSE. Nothing here flips verified to TRUE;
  that is a deliberate human action (see mark_fact_verified), because these are the
  eligibility numbers a wrong answer could harm someone with.
- ensure_rag_indexes() creates the HNSW vector index defensively: if the server's
  pgvector is too old to support HNSW, it logs and moves on rather than failing.
"""

import logging
from typing import Optional

from services.database import get_pool

logger = logging.getLogger(__name__)


# ── Index bootstrap (guarded) ────────────────────────────────────────────────

async def ensure_rag_indexes() -> None:
    """
    Create the HNSW index on scheme_chunks.embedding if it does not exist.
    Runs outside schema.sql so an older pgvector degrades to a sequential scan
    instead of breaking app startup.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_scheme_chunks_hnsw
                ON scheme_chunks USING hnsw (embedding vector_cosine_ops)
                """
            )
            logger.info("RAG: HNSW vector index present on scheme_chunks.")
        except Exception as exc:  # pragma: no cover - depends on server pgvector version
            logger.warning(
                "RAG: could not create HNSW index (%s). Vector search will use a "
                "sequential scan. Upgrade pgvector to >= 0.5.0 for ANN search.",
                type(exc).__name__,
            )


# ── source_documents ─────────────────────────────────────────────────────────

async def upsert_source(
    *,
    source_key: str,
    title: str,
    url: str,
    jurisdiction: str,
    source_type: str,
    publisher: str,
    license: str,
    cancer_types: list[str],
) -> int:
    """Register (or refresh the metadata of) a source. Returns its id.

    Does not touch content_hash / status / fetch timestamps — those are owned by
    the ingestion run so re-registering a source never resets its freshness state.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO source_documents
                (source_key, title, url, jurisdiction, source_type, publisher, license, cancer_types)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (source_key) DO UPDATE SET
                title = EXCLUDED.title,
                url = EXCLUDED.url,
                jurisdiction = EXCLUDED.jurisdiction,
                source_type = EXCLUDED.source_type,
                publisher = EXCLUDED.publisher,
                license = EXCLUDED.license,
                cancer_types = EXCLUDED.cancer_types
            RETURNING id
            """,
            source_key, title, url, jurisdiction, source_type, publisher, license, cancer_types,
        )


async def get_source_by_key(source_key: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM source_documents WHERE source_key = $1", source_key
        )
    return dict(row) if row else None


async def list_sources(jurisdiction: Optional[str] = None) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if jurisdiction:
            rows = await conn.fetch(
                "SELECT * FROM source_documents WHERE jurisdiction = $1 ORDER BY source_key",
                jurisdiction,
            )
        else:
            rows = await conn.fetch("SELECT * FROM source_documents ORDER BY source_key")
    return [dict(r) for r in rows]


async def mark_source_fetched(
    source_id: int, content_hash: str, published_date=None
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE source_documents
            SET content_hash = $2,
                published_date = COALESCE($3::date, published_date),
                last_fetched = NOW(),
                last_error = NULL
            WHERE id = $1
            """,
            source_id, content_hash, published_date,
        )


async def set_source_status(source_id: int, status: str, error: Optional[str] = None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE source_documents SET status = $2, last_error = $3 WHERE id = $1",
            source_id, status, error,
        )


async def mark_source_verified(source_id: int) -> None:
    """Record that the current content of a source has been confirmed good."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE source_documents SET last_verified = NOW(), status = 'active', last_error = NULL WHERE id = $1",
            source_id,
        )


# ── scheme_chunks ────────────────────────────────────────────────────────────

async def replace_chunks(source_id: int, chunks: list[dict]) -> int:
    """
    Atomically replace all chunks for a source. Each chunk dict:
        {heading, content, token_estimate, embedding}
    Returns the number of chunks written.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM scheme_chunks WHERE source_id = $1", source_id)
            for i, c in enumerate(chunks):
                await conn.execute(
                    """
                    INSERT INTO scheme_chunks
                        (source_id, chunk_index, heading, content, token_estimate, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    source_id, i, c.get("heading"), c["content"],
                    c.get("token_estimate"), c.get("embedding"),
                )
    return len(chunks)


async def count_chunks(source_id: Optional[int] = None) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if source_id is not None:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM scheme_chunks WHERE source_id = $1", source_id
            )
        return await conn.fetchval("SELECT COUNT(*) FROM scheme_chunks")


# ── Retrieval ────────────────────────────────────────────────────────────────

# Only sources that have been ingested are searchable. 'pending_review' stays
# searchable (its narrative chunks are refreshed + cited with a date) — it is the
# structured facts, not the prose, that are gated behind human sign-off.
_SEARCHABLE_STATUSES = ("active", "pending_review")

# Reciprocal Rank Fusion constant. 60 is the standard value from the original RRF
# paper; it damps the influence of any single ranker's top positions.
_RRF_K = 60


async def has_active_corpus(jurisdiction: str) -> bool:
    """True if we have any ingested source for this jurisdiction to ground on."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM source_documents
                WHERE jurisdiction = $1 AND status = ANY($2)
            )
            """,
            jurisdiction, list(_SEARCHABLE_STATUSES),
        )


async def hybrid_search(
    query_embedding: list[float],
    query_text: str,
    jurisdiction: str,
    cancer_types: Optional[list[str]] = None,
    *,
    limit: int = 6,
    candidate_k: int = 20,
) -> list[dict]:
    """
    Hybrid retrieval over scheme_chunks: dense (cosine) + lexical (full-text), fused
    with Reciprocal Rank Fusion. Restricted to a jurisdiction and, optionally, to
    sources tagged with overlapping cancer types. Each row carries its provenance
    (source url / publisher / license / last_verified) so the caller can cite it.
    """
    types = list(cancer_types) if cancer_types else None
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH dense AS (
                SELECT ch.id,
                       row_number() OVER (ORDER BY ch.embedding <=> $1) AS rnk
                FROM scheme_chunks ch
                JOIN source_documents s ON s.id = ch.source_id
                WHERE s.jurisdiction = $3
                  AND s.status = ANY($7)
                  AND ch.embedding IS NOT NULL
                  AND ($4::text[] IS NULL OR s.cancer_types && $4)
                ORDER BY ch.embedding <=> $1
                LIMIT $5
            ),
            lex AS (
                SELECT ch.id,
                       row_number() OVER (
                           ORDER BY ts_rank(ch.tsv, plainto_tsquery('english', $2)) DESC
                       ) AS rnk
                FROM scheme_chunks ch
                JOIN source_documents s ON s.id = ch.source_id
                WHERE s.jurisdiction = $3
                  AND s.status = ANY($7)
                  AND ch.tsv @@ plainto_tsquery('english', $2)
                  AND ($4::text[] IS NULL OR s.cancer_types && $4)
                ORDER BY ts_rank(ch.tsv, plainto_tsquery('english', $2)) DESC
                LIMIT $5
            ),
            fused AS (
                SELECT id, SUM(1.0 / ($8 + rnk)) AS rrf
                FROM (
                    SELECT id, rnk FROM dense
                    UNION ALL
                    SELECT id, rnk FROM lex
                ) u
                GROUP BY id
            )
            SELECT ch.heading, ch.content,
                   s.source_key, s.title, s.url, s.publisher, s.license,
                   s.last_verified, s.cancer_types,
                   f.rrf AS score
            FROM fused f
            JOIN scheme_chunks ch ON ch.id = f.id
            JOIN source_documents s ON s.id = ch.source_id
            ORDER BY f.rrf DESC
            LIMIT $6
            """,
            query_embedding, query_text, jurisdiction, types,
            candidate_k, limit, list(_SEARCHABLE_STATUSES), _RRF_K,
        )
    return [dict(r) for r in rows]


# ── scheme_facts ─────────────────────────────────────────────────────────────

async def stage_facts(source_id: int, facts: list[dict]) -> int:
    """
    Insert auto-extracted facts as verified = FALSE. Existing UNVERIFIED facts for
    this source are cleared first so a re-run doesn't pile up duplicates; already
    VERIFIED facts are left untouched (a human owns those).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM scheme_facts WHERE source_id = $1 AND verified = FALSE",
                source_id,
            )
            for f in facts:
                await conn.execute(
                    """
                    INSERT INTO scheme_facts
                        (source_id, jurisdiction, programme, cancer_type, sex,
                         eligible_age_min, eligible_age_max, interval_months, cost,
                         method, notes, source_url, content_hash, verified)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13, FALSE)
                    """,
                    source_id, f["jurisdiction"], f["programme"], f["cancer_type"],
                    f.get("sex", "all"), f.get("eligible_age_min"), f.get("eligible_age_max"),
                    f.get("interval_months"), f.get("cost"), f.get("method"),
                    f.get("notes"), f.get("source_url"), f.get("content_hash"),
                )
    return len(facts)


async def list_pending_facts(jurisdiction: Optional[str] = None) -> list[dict]:
    """Facts awaiting human sign-off — the review queue."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if jurisdiction:
            rows = await conn.fetch(
                "SELECT * FROM scheme_facts WHERE verified = FALSE AND jurisdiction = $1 ORDER BY created_at",
                jurisdiction,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM scheme_facts WHERE verified = FALSE ORDER BY created_at"
            )
    return [dict(r) for r in rows]


async def mark_fact_verified(fact_id: int, verified_by: str) -> None:
    """Human sign-off. The only path that lets a fact reach users."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE scheme_facts SET verified = TRUE, verified_by = $2, verified_at = NOW() WHERE id = $1",
            fact_id, verified_by,
        )


async def get_verified_facts(jurisdiction: str, cancer_type: Optional[str] = None) -> list[dict]:
    """Verified facts only — safe to surface to users."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if cancer_type:
            rows = await conn.fetch(
                """
                SELECT * FROM scheme_facts
                WHERE verified = TRUE AND jurisdiction = $1 AND cancer_type = $2
                ORDER BY programme
                """,
                jurisdiction, cancer_type,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM scheme_facts WHERE verified = TRUE AND jurisdiction = $1 ORDER BY programme",
                jurisdiction,
            )
    return [dict(r) for r in rows]
