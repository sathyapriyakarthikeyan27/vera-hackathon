"""Companion Agent router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.companion_agent import agent as companion_agent
from services.session_store import get_session
from services.database import insert_checkin
from services import gemini

router = APIRouter()


class FollowupRequest(BaseModel):
    session_id: str


@router.post("/followup")
async def generate_followup(body: FollowupRequest):
    result = await companion_agent.generate_followup(body.session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.post("/checkin")
async def simulate_checkin(body: FollowupRequest):
    """Demo endpoint: simulates a proactive 3-days-later check-in from VERA."""
    session = await get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_name: str = session.get("user_name") or ""
    risk_profile: dict = session.get("risk_profile") or {}
    risk_level: str = risk_profile.get("risk_level", "Moderate")
    companion: dict = session.get("companion_output") or {}
    plan = companion.get("follow_up_plan") or []
    next_action = plan[0]["action"] if plan else "book your free screening"

    name_clause = f" {user_name}," if user_name else ","
    prompt = (
        f"You are VERA, a warm women's health AI companion. "
        f"It has been 3 days since{name_clause} you completed your cancer risk assessment showing {risk_level} risk. "
        f"Your next step was to: {next_action}. "
        f"Write a warm, brief 2-sentence proactive check-in message asking how she is doing and whether she has been able to take that step. "
        f"Do not repeat the full plan. Be warm and personal."
    )
    message = await gemini.generate_safe(
        prompt,
        fallback=(
            f"Hi{name_clause} just checking in — it's been a few days since your VERA assessment. "
            f"Have you had a chance to take your next step? I'm here if you need help finding the right clinic."
        ),
    )

    # Persist check-in in pgvector memory (non-fatal if it fails)
    try:
        await insert_checkin(body.session_id, "vera", message)
    except Exception:
        pass

    return {"checkin_message": message, "simulated_days": 3}


@router.get("/history")
async def checkin_history(session_id: str):
    """Return the stored check-in history for a session."""
    from services.database import get_checkin_history
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    history = await get_checkin_history(session_id)
    return {"history": history}


@router.get("/health")
async def companion_health():
    return {"agent": "Companion Agent", "status": "active"}
