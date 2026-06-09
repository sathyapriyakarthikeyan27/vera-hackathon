"""
Tests for the risk profiler agent.
Covers: _current_year() is always live, _build_timeline correctness,
and reconcile() verdicts (Agreement / Escalation / Uncertainty).
"""

import datetime
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.risk_profiler.agent import _current_year, _build_timeline


# ── _current_year ─────────────────────────────────────────────────────────────

def test_current_year_matches_today():
    assert _current_year() == datetime.date.today().year


def test_current_year_is_not_hardcoded():
    """Verify the function calls datetime rather than returning a literal."""
    future = datetime.date(2030, 6, 1)
    with patch("agents.risk_profiler.agent.datetime") as mock_dt:
        mock_dt.date.today.return_value = future
        mock_dt.date.side_effect = lambda *a, **kw: datetime.date(*a, **kw)
        from agents.risk_profiler import agent
        year = agent._current_year()
    assert year == 2030


# ── _build_timeline ───────────────────────────────────────────────────────────

def test_timeline_ends_with_current_year():
    answers = {"last_screening": "never"}
    timeline = _build_timeline(answers)
    last = timeline[-1]
    assert last["year"] == _current_year()
    assert last["status"] == "urgent"


def test_timeline_marks_missed_screenings_since_last():
    """If last screening was in 2020, every 3 years up to now is missed."""
    answers = {"last_screening": "over_5yr"}
    timeline = _build_timeline(answers)
    statuses = [t["status"] for t in timeline]
    assert "missed" in statuses
    assert "completed" in statuses


def test_timeline_never_screened_shows_missed_entries():
    answers = {"last_screening": "never"}
    timeline = _build_timeline(answers)
    missed = [t for t in timeline if t["status"] == "missed"]
    assert len(missed) >= 1


def test_timeline_recent_screening_has_no_missed():
    """A screening within the last year should produce no 'missed' entries."""
    answers = {"last_screening": "within_1yr"}
    timeline = _build_timeline(answers)
    missed = [t for t in timeline if t["status"] == "missed"]
    assert len(missed) == 0


# ── reconcile() verdicts ──────────────────────────────────────────────────────

def _make_session(original_score: str, signals: list) -> dict:
    return {
        "user_name": "Test",
        "language": "en",
        "risk_assessment": {
            "score": original_score,
            "confidence": 0.75,
            "reasoning": "Initial profile assessment.",
            "source": "profile_only",
            "pending_signals": signals,
            "reconciled": False,
            "conflict": None,
        },
        "risk_profile": {"risk_level": original_score},
        "risk_state": {"answers": {}},
    }


def _gemini_response(final_score: str, conflict: bool, uncertain: bool = False) -> str:
    return json.dumps({
        "final_score": final_score,
        "conflict": conflict,
        "uncertain": uncertain,
        "reasoning": f"Reconciled to {final_score}.",
    })


async def test_reconcile_agreement_verdict():
    """Signals agree with original score — no conflict."""
    session = _make_session("Moderate", [{"severity": "medium", "anomalies": []}])

    with patch("agents.risk_profiler.agent.get_session", new_callable=AsyncMock, return_value=session), \
         patch("agents.risk_profiler.agent.update_session", new_callable=AsyncMock), \
         patch("agents.risk_profiler.agent.gemini.generate", new_callable=AsyncMock,
               return_value=_gemini_response("Moderate", False)):

        from agents.risk_profiler.agent import reconcile
        result = await reconcile("fake-session-id")

    assert result["conflict"] is False
    assert result["reconciled"] is True


async def test_reconcile_escalation_verdict():
    """High-severity signals escalate the score — conflict detected."""
    session = _make_session(
        "Moderate",
        [{"severity": "high", "anomalies": ["12mm polyp"], "urgency_flag": True}],
    )

    with patch("agents.risk_profiler.agent.get_session", new_callable=AsyncMock, return_value=session), \
         patch("agents.risk_profiler.agent.update_session", new_callable=AsyncMock), \
         patch("agents.risk_profiler.agent.gemini.generate", new_callable=AsyncMock,
               return_value=_gemini_response("High", True)):

        from agents.risk_profiler.agent import reconcile
        result = await reconcile("fake-session-id")

    assert result["conflict"] is True
    assert result["new_score"] in ("High", "Urgent")


async def test_reconcile_no_pending_signals_returns_early():
    """If pending_signals is empty, reconcile short-circuits without calling Gemini."""
    session = _make_session("Low", [])

    with patch("agents.risk_profiler.agent.get_session", new_callable=AsyncMock, return_value=session), \
         patch("agents.risk_profiler.agent.gemini.generate", new_callable=AsyncMock) as mock_gen:

        from agents.risk_profiler.agent import reconcile
        result = await reconcile("fake-session-id")

    mock_gen.assert_not_called()
    assert result["reconciled"] is True
    assert result["conflict"] is False


async def test_reconcile_session_not_found_returns_none():
    with patch("agents.risk_profiler.agent.get_session", new_callable=AsyncMock, return_value=None):
        from agents.risk_profiler.agent import reconcile
        result = await reconcile("nonexistent-id")

    assert result is None
