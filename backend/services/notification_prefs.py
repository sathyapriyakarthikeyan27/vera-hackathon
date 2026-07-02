"""
Notification preferences store.

Holds per-user channel opt-ins, phone contact (verified via OTP), timezone,
quiet hours, and consent. The email channel uses the account email
(users.email / users.email_verified), so it is not duplicated here.
"""

import uuid
from typing import Optional

from services.database import get_pool

DEFAULT_OPTIN = {"in_app": True, "email": False, "sms": False, "whatsapp": False}
CONSENT_VERSION = "2026-07-01"
EXTERNAL_CHANNELS = ("email", "sms", "whatsapp")


def _row_to_dict(row) -> dict:
    optin = row["channel_optin"] or {}
    return {
        "channel_optin": {**DEFAULT_OPTIN, **optin},
        "phone_e164": row["phone_e164"],
        "phone_verified": row["phone_verified"],
        "timezone": row["timezone"],
        "quiet_hours_start": row["quiet_hours_start"],
        "quiet_hours_end": row["quiet_hours_end"],
        "consent_at": row["consent_at"].isoformat() if row["consent_at"] else None,
        "consent_version": row["consent_version"],
    }


def _defaults() -> dict:
    return {
        "channel_optin": dict(DEFAULT_OPTIN),
        "phone_e164": None,
        "phone_verified": False,
        "timezone": "UTC",
        "quiet_hours_start": None,
        "quiet_hours_end": None,
        "consent_at": None,
        "consent_version": None,
    }


async def get_or_default(user_id: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM notification_preferences WHERE user_id = $1", uuid.UUID(user_id)
        )
    return _row_to_dict(row) if row else _defaults()


async def upsert(
    user_id: str,
    *,
    channel_optin: Optional[dict] = None,
    phone_e164: Optional[str] = None,
    timezone: Optional[str] = None,
    quiet_hours_start: Optional[int] = None,
    quiet_hours_end: Optional[int] = None,
    give_consent: bool = False,
) -> dict:
    current = await get_or_default(user_id)
    optin = {**current["channel_optin"], **(channel_optin or {})}
    optin["in_app"] = True  # in-app can never be turned off

    tz = timezone if timezone is not None else current["timezone"]
    qh_start = quiet_hours_start if quiet_hours_start is not None else current["quiet_hours_start"]
    qh_end = quiet_hours_end if quiet_hours_end is not None else current["quiet_hours_end"]

    # Changing the phone number invalidates any prior verification.
    phone = current["phone_e164"]
    phone_verified = current["phone_verified"]
    if phone_e164 is not None and phone_e164 != current["phone_e164"]:
        phone = phone_e164 or None
        phone_verified = False

    consent_at = current["consent_at"]
    consent_version = current["consent_version"]
    if give_consent and not consent_at:
        consent_version = CONSENT_VERSION

    uid = uuid.UUID(user_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO notification_preferences
                (user_id, channel_optin, phone_e164, phone_verified, timezone,
                 quiet_hours_start, quiet_hours_end, consent_at, consent_version)
            VALUES ($1, $2, $3, $4, $5, $6, $7,
                    CASE WHEN $8 THEN NOW() ELSE NULL END, $9)
            ON CONFLICT (user_id) DO UPDATE SET
                channel_optin     = EXCLUDED.channel_optin,
                phone_e164        = EXCLUDED.phone_e164,
                phone_verified    = EXCLUDED.phone_verified,
                timezone          = EXCLUDED.timezone,
                quiet_hours_start = EXCLUDED.quiet_hours_start,
                quiet_hours_end   = EXCLUDED.quiet_hours_end,
                consent_at        = COALESCE(notification_preferences.consent_at, EXCLUDED.consent_at),
                consent_version   = COALESCE(EXCLUDED.consent_version, notification_preferences.consent_version),
                updated_at        = NOW()
            RETURNING *
            """,
            uid, optin, phone, phone_verified, tz, qh_start, qh_end,
            bool(give_consent and not consent_at), consent_version,
        )
    return _row_to_dict(row)


async def set_phone(user_id: str, phone_e164: str) -> None:
    """Store a phone pending verification (resets verified)."""
    await upsert(user_id, phone_e164=phone_e164)


async def set_phone_verified(user_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE notification_preferences SET phone_verified = TRUE, updated_at = NOW() WHERE user_id = $1",
            uuid.UUID(user_id),
        )
