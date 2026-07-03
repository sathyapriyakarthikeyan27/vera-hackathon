"""
Endpoint-level tests for the auth boundary: unauthenticated requests to
health-data endpoints must 401, refresh must rotate, and login must throttle.

Uses TestClient without the lifespan context, so no DB/Redis is required;
auth_store calls are mocked where a flow needs them.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from services import ratelimit, security


@pytest.fixture(autouse=True)
def _clean_limits(monkeypatch):
    monkeypatch.setattr("services.ratelimit.cache.get_redis", lambda: None)
    ratelimit._local.clear()
    yield
    ratelimit._local.clear()
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ── Unauthenticated access to health data is denied ─────────────────────────

def test_get_session_requires_auth(client):
    assert client.get(f"/session/{uuid.uuid4()}").status_code == 401


def test_create_session_requires_auth(client):
    assert client.post("/session", json={}).status_code == 401


def test_signup_profile_requires_auth(client):
    body = {"name": "T", "age_group": "35_44", "gender": "female", "location": "Chennai"}
    assert client.post("/session/signup", json=body).status_code == 401


def test_risk_endpoints_require_auth(client):
    sid = str(uuid.uuid4())
    assert client.post("/risk/start", json={"session_id": sid}).status_code == 401
    assert client.post(
        "/risk/answer",
        json={"session_id": sid, "question_id": "q1", "answer": "no"},
    ).status_code == 401


def test_records_upload_requires_auth(client):
    res = client.post(
        "/records/upload",
        data={"session_id": str(uuid.uuid4())},
        files={"file": ("r.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert res.status_code == 401


def test_companion_and_schemes_require_auth(client):
    sid = str(uuid.uuid4())
    assert client.post("/companion/followup", json={"session_id": sid}).status_code == 401
    assert client.post("/companion/chat", json={"session_id": sid, "message": "hi"}).status_code == 401
    assert client.post("/schemes/match", json={"session_id": sid}).status_code == 401


def test_reminders_require_auth(client):
    assert client.get("/reminders").status_code == 401


# ── Refresh rotation ─────────────────────────────────────────────────────────

USER_ID = str(uuid.uuid4())
PUBLIC_USER = {
    "id": USER_ID, "email": "me@example.com", "name": "Me",
    "email_verified": True, "created_at": "2026-01-01T00:00:00+00:00",
}


def test_refresh_without_cookie_is_401(client):
    assert client.post("/auth/refresh").status_code == 401


def test_refresh_rotates_and_sets_cookies(client):
    with patch("services.auth_store.consume_auth_token",
               new_callable=AsyncMock, return_value=USER_ID) as consume, \
         patch("services.auth_store.store_auth_token", new_callable=AsyncMock) as store, \
         patch("services.auth_store.get_user_by_id",
               new_callable=AsyncMock, return_value=PUBLIC_USER):
        client.cookies.set("vera_refresh", "old-refresh-token")
        res = client.post("/auth/refresh")

    assert res.status_code == 200
    assert res.json()["user"]["id"] == USER_ID
    # Old token consumed (single-use), a new one stored, both cookies reissued.
    consume.assert_awaited_once_with("refresh", "old-refresh-token")
    store.assert_awaited_once()
    assert "vera_access" in res.cookies
    assert "vera_refresh" in res.cookies
    assert res.cookies["vera_refresh"] != "old-refresh-token"
    # The new access cookie is a valid access JWT for this user.
    payload = security.decode_token(res.cookies["vera_access"], "access")
    assert payload and payload["sub"] == USER_ID


def test_refresh_with_invalid_token_clears_session(client):
    with patch("services.auth_store.consume_auth_token",
               new_callable=AsyncMock, return_value=None):
        client.cookies.set("vera_refresh", "revoked-or-forged")
        res = client.post("/auth/refresh")
    assert res.status_code == 401


# ── Login: wrong credentials and brute-force throttling ─────────────────────

def test_login_wrong_credentials_is_401(client):
    with patch("services.auth_store.get_user_by_email",
               new_callable=AsyncMock, return_value=None):
        res = client.post("/auth/login", json={"email": "x@example.com", "password": "wrong-pw"})
    assert res.status_code == 401


def test_login_correct_password_succeeds(client):
    row = {
        "id": uuid.UUID(USER_ID), "email": "me@example.com", "name": "Me",
        "password_hash": security.hash_password("pw12345678"),
        "email_verified": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    with patch("services.auth_store.get_user_by_email",
               new_callable=AsyncMock, return_value=row), \
         patch("services.auth_store.store_auth_token", new_callable=AsyncMock):
        res = client.post("/auth/login", json={"email": "me@example.com", "password": "pw12345678"})
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "me@example.com"
    assert "password_hash" not in res.json()["user"]
    assert "vera_access" in res.cookies


def test_login_throttles_brute_force(client):
    """The 11th attempt from one IP inside the window must be 429, not 401."""
    with patch("services.auth_store.get_user_by_email",
               new_callable=AsyncMock, return_value=None):
        for _ in range(10):
            assert client.post(
                "/auth/login", json={"email": "x@example.com", "password": "guess"}
            ).status_code == 401
        res = client.post("/auth/login", json={"email": "x@example.com", "password": "guess"})
    assert res.status_code == 429


# ── Session ownership through the API ────────────────────────────────────────

def test_foreign_session_reads_as_404(client):
    from routers.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: PUBLIC_USER

    sid = str(uuid.uuid4())
    foreign = {"session_id": sid, "user_id": str(uuid.uuid4())}  # someone else's
    with patch("services.authz.get_session", new_callable=AsyncMock, return_value=foreign):
        res = client.get(f"/session/{sid}")
    assert res.status_code == 404


def test_own_session_is_returned(client):
    from routers.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: PUBLIC_USER

    sid = str(uuid.uuid4())
    mine = {"session_id": sid, "user_id": USER_ID, "risk_profile": None}
    with patch("services.authz.get_session", new_callable=AsyncMock, return_value=mine):
        res = client.get(f"/session/{sid}")
    assert res.status_code == 200
    assert res.json()["session_id"] == sid
