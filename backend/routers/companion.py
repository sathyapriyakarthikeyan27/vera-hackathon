"""Companion Agent router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import logging

from agents.companion_agent import agent as companion_agent
from services.session_store import get_session
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
async def generate_followup(body: FollowupRequest):
    result = await companion_agent.generate_followup(body.session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Materialize the reminder schedule into durable, deduped reminder rows so the
    # notification bell can surface them. Non-fatal: never break the followup response.
    try:
        session = await get_session(body.session_id)
        user_id = session.get("user_id") if session else None
        await reminder_store.materialize(
            session_id=body.session_id,
            user_id=str(user_id) if user_id else None,
            reminder_schedule=result.get("reminder_schedule") or [],
        )
    except Exception:
        logger.warning("Reminder materialization failed for session %s", body.session_id, exc_info=False)

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
        f"You are VERA, a warm health AI companion. "
        f"It has been 3 days since{name_clause} you completed your cancer risk assessment showing {risk_level} risk. "
        f"Your next step was to: {next_action}. "
        f"Write a warm, brief 2-sentence proactive check-in message asking how they are doing and whether they have been able to take that step. "
        f"Do not repeat the full plan. Be warm and personal. No em dashes."
    )
    message = await gemini.generate_safe(
        prompt,
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
async def checkin_history(session_id: str):
    """Return the stored check-in history for a session."""
    from services.database import get_checkin_history
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    history = await get_checkin_history(session_id)
    return {"history": history}


@router.post("/chat")
async def companion_chat(body: ChatRequest):
    """Chat with VERA about uploaded records and risk profile."""
    session = await get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_name: str = session.get("user_name") or ""
    records_output: dict = session.get("records_output") or {}
    risk_assessment: dict = session.get("risk_assessment") or {}
    risk_profile: dict = session.get("risk_profile") or {}

    doc_explanation: str = records_output.get("text", "")
    doc_type: str = records_output.get("document_type", "medical document")
    risk_score: str = (
        risk_assessment.get("score")
        or risk_profile.get("risk_level", "Unknown")
    )
    risk_reasoning: str = (
        risk_assessment.get("reasoning")
        or risk_profile.get("plain_language_summary", "")
    )

    context_parts = [
        f"You are VERA, a warm and caring health AI companion.",
        f"User: {user_name or 'the user'}. Current risk level: {risk_score}.",
    ]
    if doc_explanation:
        context_parts.append(
            f"The user has uploaded a {doc_type}. Here is the plain-language explanation:\n{doc_explanation}"
        )
    if risk_reasoning:
        context_parts.append(f"Risk reasoning: {risk_reasoning}")

    context_parts += [
        f"Answer the user's question based on the above context.",
        "Rules: be warm and specific, never diagnose, no em dashes, 3-5 sentences unless more detail is needed.",
        f"User question: {body.message}",
    ]

    reply = await gemini.generate_safe(
        "\n\n".join(context_parts),
        fallback="I'm having trouble processing that right now. Please try again, or speak with your doctor for guidance.",
    )
    return {"reply": reply}


@router.get("/health")
async def companion_health():
    return {"agent": "Companion Agent", "status": "active"}
