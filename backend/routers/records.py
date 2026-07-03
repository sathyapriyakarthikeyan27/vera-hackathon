"""Records Explainer Agent router (Agent 3)."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from agents.records_explainer import agent as records_agent
from routers.auth import get_current_user
from services.authz import require_session_access

router = APIRouter()

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# The declared content type is client-controlled; the magic bytes are not.
_MAGIC_PREFIXES = {
    "application/pdf": (b"%PDF",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/jpg": (b"\xff\xd8\xff",),
}


@router.post("/upload")
async def upload_record(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    await require_session_access(session_id, user)

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Use PDF, JPG, or PNG.",
        )

    # Read at most one byte over the limit so an oversized upload is rejected
    # without ever buffering the whole file.
    content = await file.read(MAX_SIZE_BYTES + 1)
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="This file is larger than 10 MB. Please upload a smaller scan.",
        )
    if not content.startswith(_MAGIC_PREFIXES[file.content_type]):
        raise HTTPException(
            status_code=415,
            detail="This file does not look like a valid PDF, JPG, or PNG.",
        )

    result = await records_agent.analyze(
        session_id, content, file.content_type, file.filename or "document"
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/health")
async def records_health():
    return {"agent": "Records Explainer", "status": "active"}
