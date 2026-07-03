"""
Tests for the session store's update contract (no DB required):
column whitelisting and invalid-id handling.
"""

import pytest

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.session_store import update_session


async def test_unknown_column_is_rejected():
    """A typo'd column must fail loudly, not silently write nothing."""
    with pytest.raises(ValueError):
        await update_session("00000000-0000-0000-0000-000000000000",
                             {"risk_profil": {"oops": True}})


async def test_invalid_session_id_returns_none():
    assert await update_session("not-a-uuid", {"user_name": "X"}) is None
