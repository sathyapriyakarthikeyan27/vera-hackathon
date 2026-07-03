"""Companion Agent router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import logging
import os

from agents.companion_agent import agent as companion_agent
from agents.companion_agent import prompts as companion_prompts
from routers.auth import get_current_user
from services.authz import require_session_access
from services.database import insert_checkin
from services import gemini, reminder_store

logger = logging.getLogger(__name__)

router = APIRouter()


class FollowupRequest(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/followup")
async def generate_followup(body: FollowupRequest, user: dict = Depends(get_current_user)):
    session = await require_session_access(body.session_id, user)
    result = await companion_agent.generate_followup(body.session_id)

    # Materialize the reminder schedule into durable, deduped reminder rows so the
    # notification bell can surface them. Non-fatal: never break the followup response.
    try:
        user_id = session.get("user_id")
        await reminder_store.materialize(
            session_id=body.session_id,
            user_id=str(user_id) if user_id else None,
            reminder_schedule=(result or {}).get("reminder_schedule") or [],
        )
    except Exception:
        logger.warning("Reminder materialization failed for session %s", body.session_id, exc_info=False)

    return result


@router.post("/checkin", include_in_schema=False)
async def simulate_checkin(body: FollowupRequest, user: dict = Depends(get_current_user)):
    """Internal testing endpoint: simulates a proactive 3-days-later check-in.

    Hidden in production (404) — real check-ins are driven by the scheduler.
    Enable in dev/staging with ENABLE_TEST_ENDPOINTS=true.
    """
    if os.getenv("ENABLE_TEST_ENDPOINTS", "false").strip().lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    session = await require_session_access(body.session_id, user)

    user_name: str = session.get("user_name") or ""
    risk_profile: dict = session.get("risk_profile") or {}
    risk_level: str = risk_profile.get("risk_level", "Moderate")
    companion: dict = session.get("companion_output") or {}
    plan = companion.get("follow_up_plan") or []
    next_action = plan[0]["action"] if plan else "book your free screening"

    name_clause = f" {user_name}," if user_name else ","
    message = await gemini.generate_safe(
        companion_prompts.checkin_prompt(name_clause, risk_level, next_action),
        fallback=(
            f"Hi{name_clause} just checking in. It's been a few days since your VERA assessment. "
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
async def checkin_history(session_id: str, user: dict = Depends(get_current_user)):
    """Return the stored check-in history for a session."""
    from services.database import get_checkin_history
    await require_session_access(session_id, user)
    history = await get_checkin_history(session_id)
    return {"history": history}


@router.post("/chat")
async def companion_chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    """Chat with VERA about uploaded records and risk profile."""
    session = await require_session_access(body.session_id, user)

    user_name: str = session.get("user_name") or ""
    records_output: dict = session.get("records_output") or {}
    risk_assessment: dict = session.get("risk_assessment") or {}
    risk_profile: dict = session.get("risk_profile") or {}

    prompt = companion_prompts.chat_prompt(
        user_name=user_name,
        risk_score=(
            risk_assessment.get("score")
            or risk_profile.get("risk_level", "Unknown")
        ),
        doc_type=records_output.get("document_type", "medical document"),
        doc_explanation=records_output.get("text", ""),
        risk_reasoning=(
            risk_assessment.get("reasoning")
            or risk_profile.get("plain_language_summary", "")
        ),
        message=body.message,
    )

    reply = await gemini.generate_safe(
        prompt,
        fallback="I'm having trouble processing that right now. Please try again, or speak with your doctor for guidance.",
    )
    return {"reply": reply}


@router.get("/health")
async def companion_health():
    return {"agent": "Companion Agent", "status": "active"}
