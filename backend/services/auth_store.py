"""
Auth persistence: users, oauth accounts, and revocable auth tokens.

Access tokens are stateless JWTs (see services.security). Everything that must be
revocable or single-use (refresh, email verification, password reset) is stored
here as a SHA-256 hash with a type and an expiry.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.database import get_pool
from services import security


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _public_user(row) -> dict:
    """Shape a user row for API responses — never includes password_hash."""
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "email_verified": row["email_verified"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


# ── Users ────────────────────────────────────────────────────────────────────

async def create_user(
    email: str,
    password_hash: Optional[str],
    name: Optional[str],
    email_verified: bool = False,
) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (email, password_hash, name, email_verified)
            VALUES (lower($1), $2, $3, $4)
            RETURNING id, email, name, email_verified, created_at
            """,
            email, password_hash, name, email_verified,
        )
    return _public_user(row)


async def get_user_by_email(email: str) -> Optional[dict]:
    """Returns the full row INCLUDING password_hash — for internal auth only."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = lower($1)", email)
    return dict(row) if row else None


async def get_user_by_id(user_id: str) -> Optional[dict]:
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, name, email_verified, created_at FROM users WHERE id = $1",
            uid,
        )
    return _public_user(row) if row else None


async def set_email_verified(user_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET email_verified = TRUE, updated_at = NOW() WHERE id = $1",
            uuid.UUID(user_id),
        )


async def set_password(user_id: str, password_hash: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET password_hash = $2, updated_at = NOW() WHERE id = $1",
            uuid.UUID(user_id), password_hash,
        )


# ── OAuth accounts ───────────────────────────────────────────────────────────

async def get_user_by_oauth(provider: str, provider_account_id: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.name, u.email_verified, u.created_at
            FROM oauth_accounts oa
            JOIN users u ON u.id = oa.user_id
            WHERE oa.provider = $1 AND oa.provider_account_id = $2
            """,
            provider, provider_account_id,
        )
    return _public_user(row) if row else None


async def link_oauth_account(user_id: str, provider: str, provider_account_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO oauth_accounts (user_id, provider, provider_account_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (provider, provider_account_id) DO NOTHING
            """,
            uuid.UUID(user_id), provider, provider_account_id,
        )


# ── Revocable / single-use tokens ────────────────────────────────────────────

async def store_auth_token(user_id: str, token_type: str, raw_token: str, ttl_seconds: int) -> None:
    expires = _now() + timedelta(seconds=ttl_seconds)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO auth_tokens (user_id, token_hash, token_type, expires_at)
            VALUES ($1, $2, $3, $4)
            """,
            uuid.UUID(user_id), security.hash_token(raw_token), token_type, expires,
        )


async def consume_auth_token(token_type: str, raw_token: str) -> Optional[str]:
    """
    Validate a token: correct type, not used, not expired. Marks it used and
    returns the owning user_id, or None if invalid. Atomic via UPDATE ... RETURNING.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE auth_tokens
            SET used = TRUE
            WHERE id = (
                SELECT id FROM auth_tokens
                WHERE token_hash = $1 AND token_type = $2
                  AND used = FALSE AND expires_at > NOW()
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING user_id
            """,
            security.hash_token(raw_token), token_type,
        )
    return str(row["user_id"]) if row else None


async def consume_user_token(user_id: str, token_type: str, raw_token: str) -> bool:
    """Like consume_auth_token but scoped to a specific user (e.g. phone OTP)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE auth_tokens
            SET used = TRUE
            WHERE id = (
                SELECT id FROM auth_tokens
                WHERE token_hash = $1 AND token_type = $2 AND user_id = $3
                  AND used = FALSE AND expires_at > NOW()
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
            """,
            security.hash_token(raw_token), token_type, uuid.UUID(user_id),
        )
    return row is not None


async def revoke_refresh_tokens(user_id: str) -> None:
    """Invalidate all outstanding refresh tokens for a user (logout / reset)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE auth_tokens SET used = TRUE WHERE user_id = $1 AND token_type = 'refresh' AND used = FALSE",
            uuid.UUID(user_id),
        )


# ── Session linking ──────────────────────────────────────────────────────────

async def attach_session_to_user(session_id: str, user_id: str) -> bool:
    """Bind an anonymous VERA session to an authenticated user."""
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE sessions SET user_id = $2 WHERE session_id = $1",
            sid, uuid.UUID(user_id),
        )
    return result.split()[-1] != "0"
