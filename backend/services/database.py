"""
Async PostgreSQL connection pool (asyncpg) with pgvector support.
JSONB columns are automatically encoded/decoded as Python dicts.
"""

import json
import os
from typing import Optional

import asyncpg
from pgvector.asyncpg import register_vector

_pool: Optional[asyncpg.Pool] = None


async def _init_conn(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await register_vector(conn)


async def _ensure_vector_extension(dsn: str) -> None:
    """Create the pgvector extension using a plain connection before the pool registers the type."""
    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    finally:
        await conn.close()


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ["DATABASE_URL"]
        await _ensure_vector_extension(dsn)
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
            init=_init_conn,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def insert_checkin(session_id: str, role: str, content: str, embedding: Optional[list] = None) -> None:
    import uuid
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO checkin_memory (session_id, role, content, embedding)
            VALUES ($1, $2, $3, $4)
            """,
            uuid.UUID(session_id), role, content, embedding,
        )


async def get_checkin_history(session_id: str, limit: int = 10) -> list[dict]:
    import uuid
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content, created_at
            FROM checkin_memory
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            uuid.UUID(session_id), limit,
        )
    return [
        {"role": r["role"], "content": r["content"], "created_at": r["created_at"].isoformat()}
        for r in rows
    ]


async def search_schemes(embedding: list[float], country: str, limit: int = 4) -> list[dict]:
    """pgvector cosine similarity search for schemes matching location + cancer type."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT scheme_name, content, metadata,
                   1 - (embedding <=> $1) AS similarity
            FROM scheme_data
            WHERE ($2 = '' OR country ILIKE $2 OR $2 ILIKE '%' || country || '%')
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            embedding, country, limit,
        )
    return [
        {
            "scheme_name": r["scheme_name"],
            "content": r["content"],
            "metadata": r["metadata"],
            "similarity": float(r["similarity"]),
        }
        for r in rows
    ]


async def count_schemes() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM scheme_data")


async def insert_scheme(scheme_name: str, country: str, cancer_types: list, content: str, metadata: dict, embedding: Optional[list]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scheme_data (scheme_name, country, cancer_types, content, metadata, embedding)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            scheme_name, country, cancer_types, content, metadata, embedding,
        )
