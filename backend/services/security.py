"""
Security primitives for auth: Argon2 password hashing, JWT access tokens,
opaque token generation, and token hashing for at-rest storage.

Access tokens are stateless JWTs (short-lived). Refresh / email-verify /
password-reset tokens are opaque random strings, stored hashed in auth_tokens
so they are revocable and single-use.
"""

import hashlib
import os
import secrets
import time
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

_ph = PasswordHasher()

_ALGO = "HS256"

# Token lifetimes (seconds). Overridable via env.
ACCESS_TTL = int(os.getenv("ACCESS_TOKEN_TTL", "900"))          # 15 minutes
REFRESH_TTL = int(os.getenv("REFRESH_TOKEN_TTL", "2592000"))    # 30 days
EMAIL_VERIFY_TTL = int(os.getenv("EMAIL_VERIFY_TTL", "86400"))  # 24 hours
RESET_TTL = int(os.getenv("PASSWORD_RESET_TTL", "3600"))        # 1 hour


_DEV_FALLBACK_SECRET = "dev-insecure-secret-change-me"


def _secret() -> str:
    # Fall back to SESSION_SECRET so the app runs without a separate JWT_SECRET.
    return (
        os.getenv("JWT_SECRET")
        or os.getenv("SESSION_SECRET")
        or _DEV_FALLBACK_SECRET
    )


def validate_secrets_on_startup() -> None:
    """
    Fail closed in production. With the dev fallback secret anyone can forge
    access tokens for any user, so refuse to boot rather than run insecurely.
    """
    env = os.getenv("APP_ENV", "development").strip().lower()
    if env == "production" and _secret() == _DEV_FALLBACK_SECRET:
        raise RuntimeError(
            "APP_ENV=production but neither JWT_SECRET nor SESSION_SECRET is set. "
            "Refusing to start with the insecure development secret."
        )


# ── Passwords ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return _ph.verify(password_hash, password)
    except Argon2Error:
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _ph.check_needs_rehash(password_hash)
    except Argon2Error:
        return False


# ── JWT access tokens ────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "type": "access", "iat": now, "exp": now + ACCESS_TTL}
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[dict]:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload


# ── OAuth state (signed, short-lived, stateless) ─────────────────────────────

def create_state_token(extra: Optional[dict] = None, ttl: int = 600) -> str:
    now = int(time.time())
    payload = {
        "type": "oauth_state",
        "iat": now,
        "exp": now + ttl,
        "nonce": secrets.token_urlsafe(16),
        **(extra or {}),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


# ── Opaque tokens (refresh / email-verify / password-reset) ──────────────────

def new_token() -> str:
    """Cryptographically-random opaque token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hash for storing tokens at rest (never store the raw value)."""
    return hashlib.sha256(token.encode()).hexdigest()
