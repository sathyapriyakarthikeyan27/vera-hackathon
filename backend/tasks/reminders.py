"""
Celery tasks for reminder scheduling and delivery.

- `reminders.dispatch_due` (Beat, periodic): claims reminders whose due_at has
  passed and are still pending, using FOR UPDATE SKIP LOCKED so multiple workers
  never grab the same row, then enqueues one delivery task per reminder.
- `reminders.deliver`: delivers a single reminder across its channels with retry.

Celery workers are sync processes, so each task opens its own short-lived asyncpg
connection via asyncio.run (the FastAPI pool lives in a different process/loop).
"""

import asyncio
import json
import logging
import os
import uuid

import asyncpg

from celery_app import celery
from services import channels

logger = logging.getLogger(__name__)

CLAIM_LIMIT = int(os.getenv("REMINDER_CLAIM_LIMIT", "200"))


def _dsn() -> str:
    return os.environ["DATABASE_URL"]


# ── Dispatch (Beat) ──────────────────────────────────────────────────────────

async def _claim_due_ids() -> list[str]:
    conn = await asyncpg.connect(_dsn())
    try:
        rows = await conn.fetch(
            """
            UPDATE reminders
            SET status = 'scheduled'
            WHERE id IN (
                SELECT id FROM reminders
                WHERE status = 'pending' AND due_at <= NOW()
                ORDER BY due_at
                LIMIT $1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
            """,
            CLAIM_LIMIT,
        )
        return [str(r["id"]) for r in rows]
    finally:
        await conn.close()


@celery.task(name="reminders.dispatch_due")
def dispatch_due() -> int:
    ids = asyncio.run(_claim_due_ids())
    for rid in ids:
        deliver.delay(rid)
    if ids:
        logger.info("Dispatched %d due reminder(s)", len(ids))
    return len(ids)


# ── Delivery (worker) ────────────────────────────────────────────────────────

async def _resolve_delivery(conn, user_id) -> tuple[list[str], dict]:
    """
    From the user's verified preferences, resolve the channels to deliver on and
    the recipient contact (verified email / phone only). Returns (channels, contact).
    """
    channels_ = ["in_app"]  # always on
    contact: dict = {}
    if not user_id:
        return channels_, contact

    urow = await conn.fetchrow("SELECT email, email_verified FROM users WHERE id = $1", user_id)
    if urow and urow["email_verified"]:
        contact["email"] = urow["email"]

    prow = await conn.fetchrow(
        "SELECT channel_optin, phone_e164, phone_verified FROM notification_preferences WHERE user_id = $1",
        user_id,
    )
    if not prow:
        return channels_, contact

    optin = prow["channel_optin"]
    if isinstance(optin, str):
        optin = json.loads(optin)
    optin = optin or {}
    if prow["phone_e164"] and prow["phone_verified"]:
        contact["phone_e164"] = prow["phone_e164"]

    if optin.get("email") and contact.get("email"):
        channels_.append("email")
    if optin.get("sms") and contact.get("phone_e164"):
        channels_.append("sms")
    if optin.get("whatsapp") and contact.get("phone_e164"):
        channels_.append("whatsapp")
    return channels_, contact


async def _deliver_one(reminder_id: str) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        row = await conn.fetchrow(
            "SELECT id, user_id, message, channels, status FROM reminders WHERE id = $1",
            uuid.UUID(reminder_id),
        )
        if not row:
            logger.warning("Reminder %s not found for delivery", reminder_id)
            return
        if row["status"] not in ("scheduled", "failed"):
            return  # already delivered / read / dismissed

        reminder = dict(row)
        chans, contact = await _resolve_delivery(conn, row["user_id"])
        ok = True
        for ch in chans:
            ok = await channels.deliver(ch, reminder, contact) and ok

        if ok:
            await conn.execute(
                "UPDATE reminders SET status = 'sent', sent_at = NOW(), attempts = attempts + 1, last_error = NULL WHERE id = $1",
                row["id"],
            )
        else:
            await conn.execute(
                "UPDATE reminders SET attempts = attempts + 1, last_error = $2 WHERE id = $1",
                row["id"], "one or more channels failed",
            )
            raise RuntimeError("channel delivery failed")
    finally:
        await conn.close()


async def _mark_failed(reminder_id: str) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute(
            "UPDATE reminders SET status = 'failed' WHERE id = $1",
            uuid.UUID(reminder_id),
        )
    finally:
        await conn.close()


@celery.task(name="reminders.deliver", bind=True, max_retries=3, default_retry_delay=30)
def deliver(self, reminder_id: str) -> None:
    try:
        asyncio.run(_deliver_one(reminder_id))
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("Reminder %s failed after retries: %s", reminder_id, type(exc).__name__)
            asyncio.run(_mark_failed(reminder_id))
