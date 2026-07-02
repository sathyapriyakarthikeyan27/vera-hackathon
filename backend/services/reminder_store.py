"""
Reminder persistence (Phase 1 — in-app notifications).

Reminders are materialized from the companion agent's `reminder_schedule` into
durable rows, deduped so regenerating the plan never creates duplicates. In-app
delivery is passive: a reminder is "due" once due_at <= now(). Scheduled external
delivery (email / SMS / WhatsApp) arrives in later phases.
"""

import hashlib
import uuid
from datetime import datetime, time, timezone
from typing import Optional

from services.database import get_pool


def _dedupe_key(owner: str, source: str, date: str, message: str) -> str:
    raw = f"{owner}|{source}|{date}|{message}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _parse_due(date_str: str) -> Optional[datetime]:
    """A 'YYYY-MM-DD' schedule date becomes 09:00 UTC on that day."""
    try:
        d = datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError):
        return None
    return datetime.combine(d, time(hour=9), tzinfo=timezone.utc)


def _row_to_dict(row) -> dict:
    now = datetime.now(timezone.utc)
    due_at = row["due_at"]
    return {
        "id": str(row["id"]),
        "source": row["source"],
        "title": row["title"],
        "message": row["message"],
        "due_at": due_at.isoformat(),
        "status": row["status"],
        "due": due_at <= now,  # in-app "fired" flag
    }


async def materialize(
    session_id: Optional[str],
    user_id: Optional[str],
    reminder_schedule: list,
    source: str = "companion",
) -> int:
    """Persist a companion reminder_schedule as rows. Idempotent via dedupe_key."""
    if not reminder_schedule:
        return 0
    owner = user_id or session_id or "anon"
    sid = uuid.UUID(session_id) if session_id else None
    uid = uuid.UUID(user_id) if user_id else None

    inserted = 0
    pool = await get_pool()
    async with pool.acquire() as conn:
        for item in reminder_schedule:
            message = (item or {}).get("message")
            date = (item or {}).get("date")
            due_at = _parse_due(date) if date else None
            if not message or not due_at:
                continue
            key = _dedupe_key(owner, source, date, message)
            result = await conn.execute(
                """
                INSERT INTO reminders (user_id, session_id, source, message, due_at, dedupe_key)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (dedupe_key) DO NOTHING
                """,
                uid, sid, source, message, due_at, key,
            )
            if result.split()[-1] != "0":
                inserted += 1
    return inserted


async def list_for_user(user_id: str) -> dict:
    """Active (non-dismissed) reminders for a user, plus the due+unread count."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, source, title, message, due_at, status
            FROM reminders
            WHERE user_id = $1 AND status <> 'dismissed'
            ORDER BY due_at ASC
            """,
            uuid.UUID(user_id),
        )
    items = [_row_to_dict(r) for r in rows]
    # Due and not yet acted on. Delivery states (pending/scheduled/sent/failed) all
    # count — the in-app reminder is visible regardless of external-channel state.
    unread_due = sum(1 for i in items if i["due"] and i["status"] not in ("read", "dismissed"))
    return {"reminders": items, "unread_due": unread_due}


async def mark_read(reminder_id: str, user_id: str) -> bool:
    try:
        rid = uuid.UUID(reminder_id)
    except (ValueError, TypeError):
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE reminders SET status = 'read', read_at = NOW()
            WHERE id = $1 AND user_id = $2 AND status <> 'dismissed'
            """,
            rid, uuid.UUID(user_id),
        )
    return result.split()[-1] != "0"


async def dismiss(reminder_id: str, user_id: str) -> bool:
    try:
        rid = uuid.UUID(reminder_id)
    except (ValueError, TypeError):
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE reminders SET status = 'dismissed' WHERE id = $1 AND user_id = $2",
            rid, uuid.UUID(user_id),
        )
    return result.split()[-1] != "0"
