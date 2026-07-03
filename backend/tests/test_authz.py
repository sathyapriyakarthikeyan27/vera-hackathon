"""
Tests for services/authz.require_session_access — the ownership gate in front
of every session-scoped health-data endpoint.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.authz import require_session_access

USER = {"id": "11111111-1111-1111-1111-111111111111", "email": "me@example.com"}
OTHER_ID = "22222222-2222-2222-2222-222222222222"
SID = "33333333-3333-3333-3333-333333333333"


def _patched(session, attach_result=True):
    return (
        patch("services.authz.get_session", new_callable=AsyncMock, return_value=session),
        patch("services.authz.auth_store.attach_session_to_user",
              new_callable=AsyncMock, return_value=attach_result),
    )


async def test_missing_session_is_404():
    p_get, p_attach = _patched(None)
    with p_get, p_attach:
        with pytest.raises(HTTPException) as exc:
            await require_session_access(SID, USER)
    assert exc.value.status_code == 404


async def test_foreign_session_is_404_not_403():
    """Another user's session must look identical to a missing one (no probing)."""
    p_get, p_attach = _patched({"session_id": SID, "user_id": OTHER_ID})
    with p_get, p_attach as attach:
        with pytest.raises(HTTPException) as exc:
            await require_session_access(SID, USER)
    assert exc.value.status_code == 404
    attach.assert_not_awaited()  # never attempts to re-bind someone else's session


async def test_owner_gets_session():
    session = {"session_id": SID, "user_id": USER["id"]}
    p_get, p_attach = _patched(session)
    with p_get, p_attach as attach:
        result = await require_session_access(SID, USER)
    assert result is session
    attach.assert_not_awaited()


async def test_unowned_session_is_claimed():
    session = {"session_id": SID, "user_id": None}
    p_get, p_attach = _patched(session, attach_result=True)
    with p_get, p_attach as attach:
        result = await require_session_access(SID, USER)
    attach.assert_awaited_once_with(SID, USER["id"])
    assert result["user_id"] == USER["id"]


async def test_lost_claim_race_is_404():
    """If another user claims the session between read and bind, deny access."""
    session = {"session_id": SID, "user_id": None}
    p_get, p_attach = _patched(session, attach_result=False)
    with p_get, p_attach:
        with pytest.raises(HTTPException) as exc:
            await require_session_access(SID, USER)
    assert exc.value.status_code == 404
