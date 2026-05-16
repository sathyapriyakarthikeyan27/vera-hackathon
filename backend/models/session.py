from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
import uuid


# ── Shared Risk Assessment Object (the collaboration bus) ─────────────────────

class RiskAssessmentConflict(BaseModel):
    original_score: str
    new_score: str
    reason: str
    shown_to_user: bool = False


class RiskAssessment(BaseModel):
    score: str = "Moderate"              # Agent 1 owns this field
    confidence: float = 0.7
    source: str = "profile_only"        # profile_only | profile+records
    pending_signals: list[dict] = []    # Agent 3 writes here
    reconciled: bool = True             # False = Agent 1 reconciliation needed
    conflict: Optional[RiskAssessmentConflict] = None


# ── Risk Profile ──────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    year: int
    event: str
    status: str  # completed | missed | urgent


class RiskProfile(BaseModel):
    risk_level: str           # Low | Moderate | High | Urgent
    risk_score: int           # 0–15
    cancer_types_flagged: list[str]
    screening_gap_years: Optional[int] = None
    timeline: list[TimelineEvent] = []
    plain_language_summary: str
    disclaimer: str = (
        "This is not a medical diagnosis. VERA provides risk awareness only. "
        "Please consult a qualified doctor."
    )


# ── Scheme Navigator ──────────────────────────────────────────────────────────

class Clinic(BaseModel):
    name: str
    distance_km: float
    address: str
    female_doctor_available: bool
    cost: str                  # Free | Subsidized | Paid
    next_available: Optional[str] = None
    contact: Optional[str] = None
    appointment_url: Optional[str] = None
    services: list[str] = []


class SchemeMatch(BaseModel):
    scheme_name: str
    description: str
    eligibility_summary: str
    coverage: str
    url: Optional[str] = None


class SchemesOutput(BaseModel):
    matched_schemes: list[SchemeMatch] = []
    nearest_clinics: list[Clinic] = []


# ── Education ─────────────────────────────────────────────────────────────────

class EducationSection(BaseModel):
    title: str
    content: str


class EducationOutput(BaseModel):
    video_url: Optional[str] = None
    personalized_intro: str
    text_summary: str
    language: str
    cancer_type: str
    sections: list[EducationSection] = []


# ── Companion ─────────────────────────────────────────────────────────────────

class FollowUpItem(BaseModel):
    date: str
    action: str
    location: Optional[str] = None
    contact: Optional[str] = None


class CompanionOutput(BaseModel):
    greeting: str
    follow_up_plan: list[FollowUpItem] = []
    family_message_drafts: dict[str, str] = {}  # {"en": "...", "hi": "...", "ta": "..."}
    reminder_schedule: list[dict[str, str]] = []


# ── Session (top-level) ───────────────────────────────────────────────────────

class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    language: str = "en"
    user_name: Optional[str] = None

    # Intermediate state for the Risk Profiler conversation
    risk_state: Optional[dict[str, Any]] = None

    # Shared collaboration object — all agents read/write via this
    risk_assessment: Optional[RiskAssessment] = None

    # Populated progressively as user moves through VERA
    risk_profile: Optional[RiskProfile] = None
    schemes_output: Optional[SchemesOutput] = None
    education_output: Optional[EducationOutput] = None
    companion_output: Optional[CompanionOutput] = None

    # Tracks which agents have run
    completed_agents: list[str] = []
