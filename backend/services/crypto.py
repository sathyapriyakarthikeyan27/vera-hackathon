"""
Field-level encryption at rest for health data (AES-128-CBC + HMAC via Fernet).

Design:
  - Application-layer, not pgcrypto-in-SQL: the key never appears in SQL text,
    so it cannot leak into pg_stat_statements, slow-query logs, or backups of
    the statement log. The database only ever sees ciphertext.
  - Envelope format keeps column types unchanged (no migration of schema):
      dicts   -> {"__enc": "<fernet token>"}   (still valid JSONB)
      strings -> "enc::v1::<fernet token>"     (still valid VARCHAR/TEXT)
  - Reads are tolerant of legacy plaintext rows (pre-encryption data decodes
    as-is); a startup sweep re-encrypts them once a key is configured.
  - Key: VERA_ENCRYPTION_KEY (a Fernet key). Generate with:
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    Required in production (fail-closed at startup). Without a key in dev the
    module is a passthrough. LOSING THE KEY MEANS LOSING THE DATA — store it
    in a secret manager and keep backups of both key and database.

What is encrypted: sessions.user_name + the health JSONB columns (risk_state,
risk_assessment, risk_profile, records_output, companion_output) and
checkin_memory.content. Generic non-personal outputs (schemes, education) and
reminders.message are not encrypted; reminders is a documented follow-up.
"""

import json
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

ENC_KEY = "__enc"
STR_PREFIX = "enc::v1::"

_fernet: Optional[Fernet] = None
_loaded = False


def _get_fernet() -> Optional[Fernet]:
    global _fernet, _loaded
    if not _loaded:
        _loaded = True
        key = os.getenv("VERA_ENCRYPTION_KEY", "").strip()
        if not key:
            logger.warning(
                "VERA_ENCRYPTION_KEY not set — health data will be stored UNENCRYPTED. "
                "Fine for local dev; production refuses to start this way."
            )
        else:
            _fernet = Fernet(key.encode())  # raises ValueError on a malformed key
    return _fernet


def enabled() -> bool:
    return _get_fernet() is not None


def validate_key_on_startup() -> None:
    """Fail closed: production must have a valid encryption key."""
    env = os.getenv("APP_ENV", "development").strip().lower()
    try:
        fernet = _get_fernet()
    except Exception as exc:
        raise RuntimeError(
            "VERA_ENCRYPTION_KEY is set but not a valid Fernet key. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        ) from exc
    if env == "production" and fernet is None:
        raise RuntimeError(
            "APP_ENV=production requires VERA_ENCRYPTION_KEY so health data is "
            "encrypted at rest. Refusing to start without it."
        )


# ── Dict (JSONB) envelope ────────────────────────────────────────────────────

def encrypt_dict(value: Optional[dict]) -> Optional[dict]:
    fernet = _get_fernet()
    if value is None or fernet is None or not isinstance(value, dict):
        return value
    if ENC_KEY in value:
        return value  # already encrypted
    token = fernet.encrypt(json.dumps(value).encode()).decode()
    return {ENC_KEY: token}


def decrypt_dict(value):
    """Decrypt an envelope; pass legacy plaintext through unchanged.

    A token that cannot be decrypted (wrong/rotated key) logs an error and
    returns None for that field — degrading one field beats bricking every
    authenticated request, and the error is loud in logs."""
    if not isinstance(value, dict) or ENC_KEY not in value:
        return value
    fernet = _get_fernet()
    if fernet is None:
        logger.error("Encrypted field present but VERA_ENCRYPTION_KEY is not set.")
        return None
    try:
        return json.loads(fernet.decrypt(value[ENC_KEY].encode()))
    except (InvalidToken, ValueError):
        logger.error("Failed to decrypt field — was VERA_ENCRYPTION_KEY rotated without re-encrypting?")
        return None


def is_encrypted_dict(value) -> bool:
    return isinstance(value, dict) and ENC_KEY in value


# ── String envelope ──────────────────────────────────────────────────────────

def encrypt_str(value: Optional[str]) -> Optional[str]:
    fernet = _get_fernet()
    if value is None or fernet is None or not isinstance(value, str):
        return value
    if value.startswith(STR_PREFIX):
        return value  # already encrypted
    return STR_PREFIX + fernet.encrypt(value.encode()).decode()


def decrypt_str(value):
    if not isinstance(value, str) or not value.startswith(STR_PREFIX):
        return value
    fernet = _get_fernet()
    if fernet is None:
        logger.error("Encrypted field present but VERA_ENCRYPTION_KEY is not set.")
        return None
    try:
        return fernet.decrypt(value[len(STR_PREFIX):].encode()).decode()
    except (InvalidToken, ValueError):
        logger.error("Failed to decrypt field — was VERA_ENCRYPTION_KEY rotated without re-encrypting?")
        return None


def is_encrypted_str(value) -> bool:
    return isinstance(value, str) and value.startswith(STR_PREFIX)


def _reset_for_tests() -> None:
    """Reload the key on next use (tests only)."""
    global _fernet, _loaded
    _fernet = None
    _loaded = False
