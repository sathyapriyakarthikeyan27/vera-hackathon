"""
Canonical VERA risk levels, ordered lowest to highest.

This is the single source of truth. Agents, prompts, and docs must use these
exact values; the frontend RiskProfile type mirrors them. "Urgent" exists so
time-sensitive cases (high risk plus active symptoms or urgent findings) can
be distinguished from ordinary high risk.
"""

RISK_LEVELS = ("Low", "Moderate", "High", "Urgent")
RISK_LEVEL_RANK = {level: i for i, level in enumerate(RISK_LEVELS)}
