import datetime
import logging
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
from dotenv import load_dotenv

from services.session_store import init_db, create_session, update_session, encrypt_existing_rows
from services.database import close_pool
from services.gemini import validate_key_on_startup
from services import auth_store, cache, crypto
from services.authz import require_session_access
from services.ratelimit import rate_limit
from services.security import validate_secrets_on_startup
from routers import risk, schemes, education, companion, records, auth, reminders, notifications
from routers.auth import get_current_user

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_secrets_on_startup()
    crypto.validate_key_on_startup()
    validate_key_on_startup()
    await init_db()
    from db.seed import seed_scheme_data
    await seed_scheme_data()
    # One-time sweep: rows written before encryption existed get encrypted now.
    await encrypt_existing_rows()
    if await cache.ping():
        logging.getLogger(__name__).info("STARTUP: Redis LLM cache connected.")
    else:
        logging.getLogger(__name__).info(
            "STARTUP: Redis LLM cache unavailable — running cache-less (fail-open)."
        )
    yield
    await cache.close_redis()
    await close_pool()


app = FastAPI(
    title="VERA API",
    description="Vital Early Risk Advisor — Proactive cancer risk companion for everyone.",
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

# Gemini-backed agent routers get a per-IP ceiling so a single client cannot
# run up model costs. Generous enough for real use (assessment auto-advance,
# uploads, chat); auth endpoints carry their own stricter limits.
_agent_limit = [Depends(rate_limit("agent", 30, 60))]

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(risk.router, prefix="/risk", tags=["Risk Profiler"], dependencies=_agent_limit)
app.include_router(schemes.router, prefix="/schemes", tags=["Scheme Navigator"], dependencies=_agent_limit)
app.include_router(education.router, prefix="/education", tags=["Education Agent"], dependencies=_agent_limit)
app.include_router(companion.router, prefix="/companion", tags=["Companion Agent"], dependencies=_agent_limit)
app.include_router(records.router, prefix="/records", tags=["Records Explainer"], dependencies=_agent_limit)
app.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "VERA API", "version": "0.1.0"}


# ── Session ───────────────────────────────────────────────────────────────────

_SUPPORTED_LANGUAGES = "^(en|hi|ta|ar|fr|es|de|it|ja|zh)$"


class SessionRequest(BaseModel):
    language: str = Field(default="en", pattern=_SUPPORTED_LANGUAGES)


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age_group: str = Field(..., pattern="^(under_25|25_34|35_44|45_54|55_plus)$")
    gender: str = Field(..., pattern="^(female|male|other)$")
    location: str = Field(..., min_length=1, max_length=200)
    language: str = Field(default="en", pattern=_SUPPORTED_LANGUAGES)
    height_cm: Optional[float] = Field(default=None, ge=0, le=300)
    weight_kg: Optional[float] = Field(default=None, ge=0, le=700)
    date_of_birth: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


@app.post(
    "/session", tags=["Session"], status_code=201,
    dependencies=[Depends(rate_limit("session_create", 20, 3600))],
)
async def create_session_endpoint(
    body: SessionRequest = SessionRequest(),
    user: dict = Depends(get_current_user),
):
    session = await create_session(body.language)
    await auth_store.attach_session_to_user(session["session_id"], user["id"])
    return session


@app.post(
    "/session/signup", tags=["Session"], status_code=201,
    dependencies=[Depends(rate_limit("session_create", 20, 3600))],
)
@app.post("/signup", tags=["Session"], status_code=201, include_in_schema=False)
async def signup_endpoint(body: SignupRequest, user: dict = Depends(get_current_user)):
    """
    Minimal-friction sign-up: creates a session and pre-fills name, age, gender,
    location, and language so the chat can start directly at health questions.
    The session is bound to the authenticated account at creation.
    """
    # VERA is for adults. DOB is optional, so this only catches declared minors;
    # age_group "under_25" without a DOB cannot be verified (known limitation).
    if body.date_of_birth:
        try:
            dob = datetime.date.fromisoformat(body.date_of_birth)
        except ValueError:
            raise HTTPException(status_code=422, detail="Please enter a valid date of birth.")
        today = datetime.date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise HTTPException(
                status_code=422,
                detail=(
                    "VERA is designed for adults aged 18 and over. If you are worried "
                    "about your health, please talk to a parent, guardian, or doctor. "
                    "They can help you get the right care."
                ),
            )

    session = await create_session(body.language)
    sid = session["session_id"]
    await auth_store.attach_session_to_user(sid, user["id"])
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
                "height_cm": body.height_cm,
                "weight_kg": body.weight_kg,
                "date_of_birth": body.date_of_birth,
                "bmi": round(body.weight_kg / ((body.height_cm / 100) ** 2), 1) if body.height_cm and body.weight_kg else None,
            },
            "current_index": 0,
            "prefilled": True,
        },
    })
    return {"session_id": sid, "language": body.language, "user_name": body.name}


@app.get("/session/{session_id}", tags=["Session"])
async def get_session_endpoint(session_id: str, user: dict = Depends(get_current_user)):
    return await require_session_access(session_id, user)
