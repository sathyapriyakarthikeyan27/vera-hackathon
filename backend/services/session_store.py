"""
Async PostgreSQL session store (asyncpg).
Each session is stored as a row in the sessions table.
JSONB columns hold agent outputs as Python dicts (codec registered in database.py).
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from services import crypto
from services.database import get_pool

logger = logging.getLogger(__name__)

# Health-data columns stored encrypted at rest (see services/crypto.py).
# schemes_output / education_output are generic non-personal content.
_ENCRYPTED_JSON_COLUMNS = {
    "risk_state", "risk_assessment", "risk_profile", "records_output", "companion_output",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _encode_updates(updates: dict) -> dict:
    """Encrypt sensitive values before they are written."""
    encoded = {}
    for col, val in updates.items():
        if col in _ENCRYPTED_JSON_COLUMNS:
            encoded[col] = crypto.encrypt_dict(val)
        elif col == "user_name":
            encoded[col] = crypto.encrypt_str(val)
        else:
            encoded[col] = val
    return encoded


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["session_id"] = str(d["session_id"])
    for ts in ("created_at", "updated_at"):
        if hasattr(d[ts], "isoformat"):
            d[ts] = d[ts].isoformat()
    for col in _ENCRYPTED_JSON_COLUMNS:
        if col in d:
            d[col] = crypto.decrypt_dict(d[col])
    if "user_name" in d:
        d["user_name"] = crypto.decrypt_str(d["user_name"])
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
        "records_output": None,
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


# Columns callers are allowed to update. Anything else is a programming error.
_UPDATABLE_COLUMNS = {
    "language", "user_name", "risk_state", "risk_assessment", "risk_profile",
    "schemes_output", "education_output", "companion_output", "records_output",
    "completed_agents",
}


async def update_session(session_id: str, updates: dict) -> Optional[dict]:
    """
    Update only the columns present in `updates` with a single targeted UPDATE.

    This deliberately avoids read-modify-write of the whole row: two concurrent
    agents writing different columns (e.g. Agent 3 writing risk_assessment while
    the companion pre-generation writes companion_output) can no longer clobber
    each other's work with stale values. Writes to the SAME column remain
    last-write-wins.
    """
    unknown = set(updates) - _UPDATABLE_COLUMNS
    if unknown:
        raise ValueError(f"update_session: unknown column(s) {sorted(unknown)}")
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return None

    set_clauses = ["updated_at = $2"]
    values: list = [sid, _now()]
    for col, val in _encode_updates(updates).items():
        values.append(val)
        set_clauses.append(f"{col} = ${len(values)}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE sessions SET {', '.join(set_clauses)} WHERE session_id = $1 RETURNING *",
            *values,
        )
    return _row_to_dict(row) if row else None


async def encrypt_existing_rows() -> int:
    """
    One-time sweep run at startup: re-write any plaintext sensitive fields
    (rows created before encryption existed) through the encrypting update
    path. No-op when no key is configured or everything is already encrypted.
    """
    if not crypto.enabled():
        return 0
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM sessions")
    changed = 0
    for row in rows:
        d = dict(row)
        updates: dict = {}
        for col in _ENCRYPTED_JSON_COLUMNS:
            val = d.get(col)
            if val is not None and not crypto.is_encrypted_dict(val):
                updates[col] = val  # plaintext — update_session re-encrypts it
        name = d.get("user_name")
        if name is not None and not crypto.is_encrypted_str(name):
            updates["user_name"] = name
        if updates:
            await update_session(str(d["session_id"]), updates)
            changed += 1

    # checkin_memory.content (Agent 4 timeline) gets the same treatment.
    async with pool.acquire() as conn:
        checkins = await conn.fetch(
            "SELECT id, content FROM checkin_memory WHERE content NOT LIKE $1",
            crypto.STR_PREFIX + "%",
        )
        for c in checkins:
            await conn.execute(
                "UPDATE checkin_memory SET content = $2 WHERE id = $1",
                c["id"], crypto.encrypt_str(c["content"]),
            )
        changed += len(checkins)

    if changed:
        logger.info("Encrypted %d pre-existing plaintext row(s) at rest.", changed)
    return changed


async def delete_session(session_id: str) -> bool:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM sessions WHERE session_id = $1", sid)
    return result.split()[-1] != "0"
