"""
Async PostgreSQL session store (asyncpg).
Each session is stored as a row in the sessions table.
JSONB columns hold agent outputs as Python dicts (codec registered in database.py).
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from services.database import get_pool


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["session_id"] = str(d["session_id"])
    for ts in ("created_at", "updated_at"):
        if hasattr(d[ts], "isoformat"):
            d[ts] = d[ts].isoformat()
    return d


async def init_db() -> None:
    """Create tables from schema.sql (idempotent — uses IF NOT EXISTS)."""
    schema_sql = (Path(__file__).parent.parent / "db" / "schema.sql").read_text()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(schema_sql)


async def create_session(language: str = "en") -> dict:
    sid = uuid.uuid4()
    now = _now()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (session_id, language, completed_agents, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            sid, language, [], now, now,
        )
    return {
        "session_id": str(sid),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "language": language,
        "user_name": None,
        "risk_state": None,
        "risk_assessment": None,
        "risk_profile": None,
        "schemes_output": None,
        "education_output": None,
        "companion_output": None,
        "completed_agents": [],
    }


async def get_session(session_id: str) -> Optional[dict]:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return None
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE session_id = $1", sid)
    return _row_to_dict(row) if row else None


async def update_session(session_id: str, updates: dict) -> Optional[dict]:
    session = await get_session(session_id)
    if session is None:
        return None
    session.update(updates)
    now = _now()
    session["updated_at"] = now.isoformat()
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return None
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE sessions SET
                language         = $2,
                user_name        = $3,
                risk_state       = $4,
                risk_assessment  = $5,
                risk_profile     = $6,
                schemes_output   = $7,
                education_output = $8,
                companion_output = $9,
                completed_agents = $10,
                updated_at       = $11
            WHERE session_id = $1
            """,
            sid,
            session.get("language", "en"),
            session.get("user_name"),
            session.get("risk_state"),
            session.get("risk_assessment"),
            session.get("risk_profile"),
            session.get("schemes_output"),
            session.get("education_output"),
            session.get("companion_output"),
            session.get("completed_agents") or [],
            now,
        )
    return session


async def delete_session(session_id: str) -> bool:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM sessions WHERE session_id = $1", sid)
    return result.split()[-1] != "0"
