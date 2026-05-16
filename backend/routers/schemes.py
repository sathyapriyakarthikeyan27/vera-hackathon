"""Scheme Navigator Agent router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.scheme_navigator import agent as scheme_agent

router = APIRouter()


class MatchRequest(BaseModel):
    session_id: str


@router.post("/match")
async def match_schemes(body: MatchRequest):
    result = await scheme_agent.match(body.session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/health")
async def schemes_health():
    return {"agent": "Scheme Navigator", "status": "active"}
