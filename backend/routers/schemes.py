"""Scheme Navigator Agent router."""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from agents.scheme_navigator import agent as scheme_agent
from agents.companion_agent import agent as companion_agent

router = APIRouter()


class MatchRequest(BaseModel):
    session_id: str


async def _pregen_companion(session_id: str) -> None:
    """Pre-generate companion plan so /companion loads instantly.

    generate_followup() returns the cached plan if one already exists and
    regenerates only when it is missing (e.g. after a reconciliation cleared
    it), so this is safe to call on every /match without redundant Gemini work.
    """
    await companion_agent.generate_followup(session_id)


@router.post("/match")
async def match_schemes(body: MatchRequest, background_tasks: BackgroundTasks):
    result = await scheme_agent.match(body.session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    background_tasks.add_task(_pregen_companion, body.session_id)
    return result


@router.get("/health")
async def schemes_health():
    return {"agent": "Scheme Navigator", "status": "active"}
