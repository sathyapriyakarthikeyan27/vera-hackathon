"""Education Agent router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.education_agent import agent as education_agent
from routers.auth import get_current_user
from services.authz import require_session_access

router = APIRouter()


class GenerateRequest(BaseModel):
    session_id: str


@router.post("/generate")
async def generate_education(body: GenerateRequest, user: dict = Depends(get_current_user)):
    await require_session_access(body.session_id, user)
    result = await education_agent.generate(body.session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/health")
async def education_health():
    return {"agent": "Education Agent", "status": "active"}
