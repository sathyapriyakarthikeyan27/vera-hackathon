"""
Session-level authorization. Every session-scoped endpoint must verify that
the session belongs to the authenticated user before touching health data.

Sessions are created unowned during profile signup and bound to the account on
first authenticated access (or explicitly via /auth/link-session). Once owned,
only the owner can read or write it. Missing and forbidden both return 404 so
session IDs cannot be probed for existence.
"""

from fastapi import HTTPException

from services import auth_store
from services.session_store import get_session


async def require_session_access(session_id: str, user: dict) -> dict:
    """Return the session if `user` owns (or successfully claims) it, else 404."""
    session = await get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    owner = session.get("user_id")
    if owner is None:
        # First authenticated touch claims the session. attach_session_to_user
        # refuses to re-bind if another user claimed it in the meantime.
        if not await auth_store.attach_session_to_user(session_id, user["id"]):
            raise HTTPException(status_code=404, detail="Session not found")
        session["user_id"] = user["id"]
    elif str(owner) != str(user["id"]):
        raise HTTPException(status_code=404, detail="Session not found")
    return session
