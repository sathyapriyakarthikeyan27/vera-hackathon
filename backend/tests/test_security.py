"""
Tests for services/security.py: password hashing, JWT lifecycle, token hashing,
and the fail-closed production secrets check.
"""

import time
from unittest.mock import patch

import pytest

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services import security


# ── Passwords ────────────────────────────────────────────────────────────────

def test_password_hash_and_verify():
    h = security.hash_password("correct horse battery")
    assert h != "correct horse battery"
    assert security.verify_password("correct horse battery", h) is True
    assert security.verify_password("wrong password", h) is False


def test_verify_password_empty_hash_is_false():
    assert security.verify_password("anything", "") is False
    assert security.verify_password("anything", None) is False


def test_fresh_hash_does_not_need_rehash():
    h = security.hash_password("pw12345678")
    assert security.needs_rehash(h) is False


# ── JWT access tokens ────────────────────────────────────────────────────────

def test_access_token_round_trip():
    token = security.create_access_token("user-123")
    payload = security.decode_token(token, "access")
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_decode_rejects_wrong_type():
    token = security.create_access_token("user-123")
    assert security.decode_token(token, "oauth_state") is None


def test_decode_rejects_garbage():
    assert security.decode_token("not-a-jwt") is None
    assert security.decode_token("") is None


def test_expired_access_token_rejected():
    real_time = time.time()
    with patch("services.security.time") as mock_time:
        # Issue the token far enough in the past that it is expired now.
        mock_time.time.return_value = real_time - security.ACCESS_TTL - 60
        token = security.create_access_token("user-123")
    assert security.decode_token(token, "access") is None


def test_token_signed_with_other_secret_rejected():
    import jwt as pyjwt
    forged = pyjwt.encode(
        {"sub": "user-123", "type": "access", "iat": int(time.time()),
         "exp": int(time.time()) + 900},
        "attacker-secret", algorithm="HS256",
    )
    assert security.decode_token(forged, "access") is None


# ── Opaque tokens ────────────────────────────────────────────────────────────

def test_new_tokens_are_unique():
    assert security.new_token() != security.new_token()


def test_hash_token_is_deterministic_and_one_way():
    t = security.new_token()
    assert security.hash_token(t) == security.hash_token(t)
    assert security.hash_token(t) != t
    assert security.hash_token(t) != security.hash_token(t + "x")


# ── Fail-closed production secrets ───────────────────────────────────────────

def test_production_without_secret_refuses_to_start(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        security.validate_secrets_on_startup()


def test_production_with_secret_starts(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "a-real-secret-value")
    security.validate_secrets_on_startup()  # must not raise


def test_development_without_secret_is_allowed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    security.validate_secrets_on_startup()  # must not raise
