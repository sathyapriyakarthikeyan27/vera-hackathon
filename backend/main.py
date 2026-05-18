from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

from services.session_store import init_db, create_session, get_session, update_session
from services.database import close_pool
from routers import risk, schemes, education, companion, records

load_dotenv()


def validate_environment() -> None:
    missing = []
    if not os.getenv("DATABASE_URL"):
        missing.append("DATABASE_URL")
    if not os.getenv("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_environment()
    await init_db()
    from db.seed import seed_scheme_data
    await seed_scheme_data()
    yield
    await close_pool()


app = FastAPI(
    title="VERA API",
    description="Vital Early Risk Advisor — Women's Cancer Prevention AI Companion",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(risk.router, prefix="/risk", tags=["Risk Profiler"])
app.include_router(schemes.router, prefix="/schemes", tags=["Scheme Navigator"])
app.include_router(education.router, prefix="/education", tags=["Education Agent"])
app.include_router(companion.router, prefix="/companion", tags=["Companion Agent"])
app.include_router(records.router, prefix="/records", tags=["Records Explainer"])


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "VERA API", "version": "0.1.0"}


# ── Session ───────────────────────────────────────────────────────────────────

class SessionRequest(BaseModel):
    language: str = Field(default="en", pattern="^(en|hi|ta)$")


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age_group: str = Field(..., pattern="^(under_25|25_34|35_44|45_54|55_plus)$")
    gender: str = Field(..., pattern="^(female|male|other)$")
    location: str = Field(..., min_length=1, max_length=200)
    language: str = Field(default="en", pattern="^(en|hi|ta)$")


@app.post("/session", tags=["Session"], status_code=201)
async def create_session_endpoint(body: SessionRequest = SessionRequest()):
    return await create_session(body.language)


@app.post("/session/signup", tags=["Session"], status_code=201)
async def signup_endpoint(body: SignupRequest):
    """
    Minimal-friction sign-up: creates a session and pre-fills name, age, gender,
    location, and language so the chat can start directly at health questions.
    """
    session = await create_session(body.language)
    sid = session["session_id"]
    await update_session(sid, {
        "user_name": body.name,
        "language": body.language,
        "risk_state": {
            "answers": {
                "user_name": body.name,
                "age_group": body.age_group,
                "gender": body.gender,
                "location": body.location,
                "language": body.language,
            },
            "current_index": 0,
            "prefilled": True,
        },
    })
    return {"session_id": sid, "language": body.language, "user_name": body.name}


@app.get("/session/{session_id}", tags=["Session"])
async def get_session_endpoint(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
