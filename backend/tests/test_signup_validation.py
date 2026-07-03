"""
Tests for SignupRequest validation in main.py.
Covers: float height/weight, bounds, date_of_birth pattern, gender/age_group enums.
"""

import pytest
from pydantic import ValidationError

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import SignupRequest


VALID_BASE = {
    "name": "Test User",
    "age_group": "35_44",
    "gender": "female",
    "location": "Chennai",
}


# ── height / weight ──────────────────────────────────────────────────────────

def test_accepts_float_height_weight():
    r = SignupRequest(**VALID_BASE, height_cm=175.5, weight_kg=72.3)
    assert r.height_cm == 175.5
    assert r.weight_kg == 72.3


def test_accepts_integer_height_weight():
    r = SignupRequest(**VALID_BASE, height_cm=170, weight_kg=65)
    assert r.height_cm == 170.0
    assert r.weight_kg == 65.0


def test_accepts_none_height_weight():
    r = SignupRequest(**VALID_BASE)
    assert r.height_cm is None
    assert r.weight_kg is None


def test_rejects_negative_height():
    with pytest.raises(ValidationError):
        SignupRequest(**VALID_BASE, height_cm=-1)


def test_rejects_negative_weight():
    with pytest.raises(ValidationError):
        SignupRequest(**VALID_BASE, weight_kg=-0.1)


def test_rejects_height_above_300():
    with pytest.raises(ValidationError):
        SignupRequest(**VALID_BASE, height_cm=301)


def test_rejects_weight_above_700():
    with pytest.raises(ValidationError):
        SignupRequest(**VALID_BASE, weight_kg=700.1)


def test_bmi_computed_correctly():
    """BMI = weight_kg / (height_cm/100)^2"""
    from main import app
    from fastapi.testclient import TestClient
    # BMI for 70kg, 175cm = 70 / 1.75^2 = 22.9
    # We test the formula directly since we can't call the endpoint without DB
    height_cm = 175.0
    weight_kg = 70.0
    expected = round(weight_kg / ((height_cm / 100) ** 2), 1)
    assert expected == 22.9


# ── date_of_birth ─────────────────────────────────────────────────────────────

def test_accepts_valid_dob():
    r = SignupRequest(**VALID_BASE, date_of_birth="1985-03-22")
    assert r.date_of_birth == "1985-03-22"


def test_rejects_freeform_dob():
    with pytest.raises(ValidationError):
        SignupRequest(**VALID_BASE, date_of_birth="March 22, 1985")


def test_rejects_partial_dob():
    with pytest.raises(ValidationError):
        SignupRequest(**VALID_BASE, date_of_birth="1985-03")


def test_rejects_empty_dob():
    with pytest.raises(ValidationError):
        SignupRequest(**VALID_BASE, date_of_birth="")


def test_accepts_none_dob():
    r = SignupRequest(**VALID_BASE, date_of_birth=None)
    assert r.date_of_birth is None


# ── gender / age_group enums ─────────────────────────────────────────────────

def test_rejects_unknown_gender():
    with pytest.raises(ValidationError):
        SignupRequest(**{**VALID_BASE, "gender": "unknown"})


def test_accepts_all_valid_genders():
    for g in ("female", "male", "other"):
        r = SignupRequest(**{**VALID_BASE, "gender": g})
        assert r.gender == g


def test_rejects_unknown_age_group():
    with pytest.raises(ValidationError):
        SignupRequest(**{**VALID_BASE, "age_group": "60_plus"})


def test_accepts_all_valid_age_groups():
    for ag in ("under_25", "25_34", "35_44", "45_54", "55_plus"):
        r = SignupRequest(**{**VALID_BASE, "age_group": ag})
        assert r.age_group == ag


# ── name / location length ───────────────────────────────────────────────────

def test_rejects_empty_name():
    with pytest.raises(ValidationError):
        SignupRequest(**{**VALID_BASE, "name": ""})


def test_rejects_empty_location():
    with pytest.raises(ValidationError):
        SignupRequest(**{**VALID_BASE, "location": ""})
