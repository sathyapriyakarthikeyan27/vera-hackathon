"""
Tests for the guideline-anchored fallback rubric, the data-completeness
confidence heuristic, and the under-18 signup gate.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.risk_profiler.agent import _profile_confidence, _rule_based_fallback
from main import app
from services import ratelimit


# ── _rule_based_fallback ─────────────────────────────────────────────────────

def test_high_risk_profile_scores_high_or_urgent():
    answers = {
        "gender": "male", "age_group": "55_plus", "family_history": "yes_colorectal",
        "smoking": "current", "last_screening": "never",
    }
    result = _rule_based_fallback(answers)
    assert result["risk_level"] in ("High", "Urgent")
    assert "colorectal" in result["cancer_types_flagged"]
    assert "lung" in result["cancer_types_flagged"]      # smoker (USPSTF LDCT signal)
    assert "prostate" in result["cancer_types_flagged"]  # male 55+
    assert result["engine"] == "rule_fallback"


def test_low_risk_profile_scores_low():
    answers = {
        "gender": "female", "age_group": "25_34", "family_history": "no",
        "smoking": "never", "last_screening": "within_1yr", "hpv_vaccine": "yes",
    }
    result = _rule_based_fallback(answers)
    assert result["risk_level"] == "Low"
    assert "cervical" in result["cancer_types_flagged"]  # screening-age female


def test_reported_symptoms_force_at_least_moderate():
    answers = {
        "gender": "female", "age_group": "25_34", "family_history": "no",
        "smoking": "never", "last_screening": "within_1yr", "hpv_vaccine": "yes",
        "symptoms": "I found a lump and I am worried",
    }
    result = _rule_based_fallback(answers)
    assert result["risk_level"] in ("Moderate", "High", "Urgent")


def test_hpv_points_only_apply_to_female_profiles():
    base = {"age_group": "25_34", "family_history": "no",
            "smoking": "never", "last_screening": "within_1yr", "hpv_vaccine": "no"}
    male = _rule_based_fallback({**base, "gender": "male"})
    female = _rule_based_fallback({**base, "gender": "female"})
    assert female["risk_score"] == male["risk_score"] + 2


def test_obesity_adds_risk_point():
    base = {"gender": "male", "age_group": "35_44", "family_history": "no",
            "smoking": "never", "last_screening": "within_1yr"}
    normal = _rule_based_fallback({**base, "bmi": 24.0})
    obese = _rule_based_fallback({**base, "bmi": 32.5})
    assert obese["risk_score"] == normal["risk_score"] + 1


def test_breast_flagged_for_screening_age_women():
    answers = {"gender": "female", "age_group": "45_54", "family_history": "no",
               "smoking": "never", "last_screening": "1_3yr"}
    result = _rule_based_fallback(answers)
    assert "breast" in result["cancer_types_flagged"]   # USPSTF 2024: 40-74


# ── _profile_confidence ──────────────────────────────────────────────────────

def test_confidence_capped_at_point_eight():
    answers = {"age_group": "45_54", "gender": "male", "family_history": "no",
               "smoking": "never", "last_screening": "never"}
    assert _profile_confidence(answers, "gemini") == 0.8


def test_confidence_drops_with_missing_answers_and_fallback_engine():
    full_gemini = _profile_confidence(
        {"age_group": "x", "gender": "x", "family_history": "x",
         "smoking": "x", "last_screening": "x"}, "gemini")
    sparse_gemini = _profile_confidence({"age_group": "x"}, "gemini")
    sparse_fallback = _profile_confidence({"age_group": "x"}, "rule_fallback")
    assert full_gemini > sparse_gemini > sparse_fallback
    assert sparse_fallback >= 0.2  # floored, never zero or negative


# ── Under-18 signup gate ─────────────────────────────────────────────────────

USER = {"id": str(uuid.uuid4()), "email": "adult@example.com", "name": None,
        "email_verified": True, "created_at": None}


@pytest.fixture
def client():
    from routers.auth import get_current_user
    ratelimit._local.clear()
    app.dependency_overrides[get_current_user] = lambda: USER
    yield TestClient(app)
    app.dependency_overrides.clear()
    ratelimit._local.clear()


def test_minor_signup_is_rejected_with_guidance(client):
    body = {"name": "Kid", "age_group": "under_25", "gender": "female",
            "location": "Chennai", "date_of_birth": "2012-05-01"}
    res = client.post("/session/signup", json=body)
    assert res.status_code == 422
    assert "18" in res.json()["detail"]


def test_adult_signup_passes_the_age_gate(client):
    sid = str(uuid.uuid4())
    body = {"name": "Adult", "age_group": "35_44", "gender": "female",
            "location": "Chennai", "date_of_birth": "1988-05-01"}
    with patch("main.create_session", new_callable=AsyncMock,
               return_value={"session_id": sid}), \
         patch("main.update_session", new_callable=AsyncMock), \
         patch("services.auth_store.attach_session_to_user",
               new_callable=AsyncMock, return_value=True):
        res = client.post("/session/signup", json=body)
    assert res.status_code == 201
    assert res.json()["session_id"] == sid
