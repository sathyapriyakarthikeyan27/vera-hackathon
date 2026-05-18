"""Risk Profiler Agent router."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.risk_profiler import agent as risk_agent

router = APIRouter()


class StartRequest(BaseModel):
    session_id: str


class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str
    key: Optional[str] = None


@router.post("/start")
async def start_risk(body: StartRequest):
    result = await risk_agent.start_assessment(body.session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.post("/answer")
async def answer_risk(body: AnswerRequest):
    result = await risk_agent.process_answer(
        body.session_id, body.question_id, body.answer, body.key
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.post("/reconcile")
async def reconcile_risk(body: StartRequest):
    result = await risk_agent.reconcile(body.session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/health")
async def risk_health():
    return {"agent": "Risk Profiler", "status": "active"}
