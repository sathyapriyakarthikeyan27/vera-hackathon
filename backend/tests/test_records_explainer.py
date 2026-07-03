"""
Tests for the records explainer agent — specifically _extract_signals,
which parses Gemini's JSON response and must handle malformed output safely.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.records_explainer.agent import _extract_signals, _FALLBACK_SIGNALS


def _mock_gemini(return_value: str):
    return patch(
        "agents.records_explainer.agent.gemini.generate_pro_multimodal",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── Happy path ───────────────────────────────────────────────────────────────

async def test_extract_valid_signals():
    payload = {
        "anomalies": ["12mm polyp, ascending colon"],
        "severity": "high",
        "confidence": 0.91,
        "specialist_signal": "Gastroenterologist",
        "urgency_flag": True,
    }
    with _mock_gemini(json.dumps(payload)):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result["severity"] == "high"
    assert result["urgency_flag"] is True
    assert result["specialist_signal"] == "Gastroenterologist"
    assert len(result["anomalies"]) == 1


async def test_extract_strips_markdown_fences():
    payload = {"anomalies": [], "severity": "low", "confidence": 0.9,
               "specialist_signal": None, "urgency_flag": False}
    wrapped = f"```json\n{json.dumps(payload)}\n```"
    with _mock_gemini(wrapped):
        result = await _extract_signals(b"fake", "image/jpeg")

    assert result["severity"] == "low"
    assert result["urgency_flag"] is False


async def test_extract_normal_document_returns_low():
    payload = {"anomalies": [], "severity": "low", "confidence": 0.95,
               "specialist_signal": None, "urgency_flag": False}
    with _mock_gemini(json.dumps(payload)):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result["severity"] == "low"
    assert result["anomalies"] == []


# ── isinstance guard (the bug that was fixed) ────────────────────────────────

async def test_returns_fallback_when_gemini_returns_array():
    """Gemini occasionally returns a JSON array instead of an object."""
    with _mock_gemini(json.dumps(["finding1", "finding2"])):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result == _FALLBACK_SIGNALS


async def test_returns_fallback_when_gemini_returns_null():
    with _mock_gemini("null"):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result == _FALLBACK_SIGNALS


async def test_returns_fallback_when_gemini_returns_plain_string():
    with _mock_gemini("Here are the findings from your document."):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result == _FALLBACK_SIGNALS


async def test_returns_fallback_when_gemini_raises():
    with patch(
        "agents.records_explainer.agent.gemini.generate_pro_multimodal",
        new_callable=AsyncMock,
        side_effect=RuntimeError("API unavailable"),
    ):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result == _FALLBACK_SIGNALS


# ── Partial / degraded responses ─────────────────────────────────────────────

async def test_missing_fields_use_defaults():
    """A dict missing optional fields should not crash — defaults fill in."""
    with _mock_gemini(json.dumps({"anomalies": ["some finding"]})):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result["severity"] == "medium"
    assert result["confidence"] == 0.7
    assert result["urgency_flag"] is False
    assert result["specialist_signal"] is None


async def test_confidence_coerced_to_float():
    payload = {"anomalies": [], "severity": "low", "confidence": "0.8",
               "specialist_signal": None, "urgency_flag": False}
    with _mock_gemini(json.dumps(payload)):
        result = await _extract_signals(b"fake", "application/pdf")

    assert isinstance(result["confidence"], float)
    assert result["confidence"] == 0.8


async def test_non_numeric_confidence_does_not_crash():
    """A non-numeric confidence from the model must not raise — default 0.7."""
    payload = {"anomalies": ["some finding"], "severity": "high",
               "confidence": "very confident", "specialist_signal": None,
               "urgency_flag": True}
    with _mock_gemini(json.dumps(payload)):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result["confidence"] == 0.7
    assert result["severity"] == "high"
    assert result["urgency_flag"] is True


async def test_invalid_severity_defaults_to_medium():
    payload = {"anomalies": [], "severity": "catastrophic", "confidence": 0.9,
               "specialist_signal": None, "urgency_flag": False}
    with _mock_gemini(json.dumps(payload)):
        result = await _extract_signals(b"fake", "application/pdf")

    assert result["severity"] == "medium"
