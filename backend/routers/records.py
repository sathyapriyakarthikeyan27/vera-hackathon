"""Records Explainer Agent router (Agent 3)."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from agents.records_explainer import agent as records_agent

router = APIRouter()

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload_record(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Use PDF, JPG, or PNG.",
        )

    result = await records_agent.analyze(session_id, file)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/health")
async def records_health():
    return {"agent": "Records Explainer", "status": "active"}
