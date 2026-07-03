"""
Tests for field-level encryption at rest (services/crypto.py) and the
session-store encode/decode paths.
"""

import pytest
from cryptography.fernet import Fernet

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services import crypto
from services.session_store import _encode_updates


@pytest.fixture
def with_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("VERA_ENCRYPTION_KEY", key)
    crypto._reset_for_tests()
    yield key
    crypto._reset_for_tests()


@pytest.fixture
def without_key(monkeypatch):
    monkeypatch.delenv("VERA_ENCRYPTION_KEY", raising=False)
    crypto._reset_for_tests()
    yield
    crypto._reset_for_tests()


# ── Dict envelope ────────────────────────────────────────────────────────────

def test_dict_round_trip(with_key):
    original = {"answers": {"family_history": "yes_colorectal"}, "score": 7}
    stored = crypto.encrypt_dict(original)
    assert crypto.is_encrypted_dict(stored)
    assert "family_history" not in str(stored)  # ciphertext leaks nothing
    assert crypto.decrypt_dict(stored) == original


def test_encrypt_dict_is_idempotent(with_key):
    once = crypto.encrypt_dict({"a": 1})
    twice = crypto.encrypt_dict(once)
    assert twice == once  # never double-wraps


def test_legacy_plaintext_dict_passes_through(with_key):
    legacy = {"score": "Moderate"}  # row written before encryption existed
    assert crypto.decrypt_dict(legacy) == legacy


def test_none_passes_through(with_key):
    assert crypto.encrypt_dict(None) is None
    assert crypto.decrypt_dict(None) is None


def test_wrong_key_degrades_to_none_not_crash(with_key, monkeypatch):
    stored = crypto.encrypt_dict({"secret": True})
    monkeypatch.setenv("VERA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto._reset_for_tests()
    assert crypto.decrypt_dict(stored) is None  # loud in logs, no exception


def test_without_key_is_passthrough(without_key):
    value = {"answers": {"smoking": "never"}}
    assert crypto.encrypt_dict(value) is value
    assert crypto.enabled() is False


# ── String envelope ──────────────────────────────────────────────────────────

def test_string_round_trip(with_key):
    stored = crypto.encrypt_str("Priya")
    assert crypto.is_encrypted_str(stored)
    assert "Priya" not in stored
    assert crypto.decrypt_str(stored) == "Priya"


def test_legacy_plaintext_string_passes_through(with_key):
    assert crypto.decrypt_str("Priya") == "Priya"


# ── Startup validation ───────────────────────────────────────────────────────

def test_production_without_key_refuses_to_start(monkeypatch, without_key):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        crypto.validate_key_on_startup()


def test_production_with_key_starts(monkeypatch, with_key):
    monkeypatch.setenv("APP_ENV", "production")
    crypto.validate_key_on_startup()  # must not raise


def test_malformed_key_fails_loudly(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("VERA_ENCRYPTION_KEY", "not-a-fernet-key")
    crypto._reset_for_tests()
    with pytest.raises(RuntimeError):
        crypto.validate_key_on_startup()
    crypto._reset_for_tests()


# ── Session store integration (pure encode path) ─────────────────────────────

def test_session_store_encodes_sensitive_columns_only(with_key):
    updates = {
        "risk_profile": {"risk_level": "High"},
        "user_name": "Priya",
        "schemes_output": {"matched_schemes": []},   # generic — stays plaintext
        "completed_agents": ["risk_profiler"],
    }
    encoded = _encode_updates(updates)
    assert crypto.is_encrypted_dict(encoded["risk_profile"])
    assert crypto.is_encrypted_str(encoded["user_name"])
    assert encoded["schemes_output"] == {"matched_schemes": []}
    assert encoded["completed_agents"] == ["risk_profiler"]
