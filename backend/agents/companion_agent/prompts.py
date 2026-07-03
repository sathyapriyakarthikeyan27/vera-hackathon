"""
Prompt templates for the Companion Agent (Agent 4), including the check-in and
chat prompts used by the companion router.

Version tags are bumped whenever prompt text changes in a way that could alter
model output.
"""

from typing import Optional

PLAN_PROMPT_VERSION = "v1"
FAMILY_MESSAGES_PROMPT_VERSION = "v1"
CHECKIN_PROMPT_VERSION = "v1"
CHAT_PROMPT_VERSION = "v1"


def plan_prompt(
    *,
    name_line: str,
    person_context: str,
    specialist: str,
    clinic_info: str,
    today: str,
    types_text: str,
    location: str,
    risk_level: str,
    doc_label: str,
    conflict: Optional[dict],
) -> str:
    if conflict and conflict.get("uncertain"):
        escalation_context = (
            f"\nIMPORTANT CONTEXT: This person uploaded their {doc_label}, which surfaced "
            f"findings that are mixed and need a specialist to review. Their risk level has NOT "
            f"changed, so do NOT say it was updated or escalated. The greeting MUST acknowledge "
            f"the {doc_label} and that a specialist should review these findings. The plan steps "
            f"should prioritise booking a specialist review soon."
        )
        urgency_note = (
            f"This person's {doc_label} surfaced uncertain findings. "
            f"The first step must be to book a specialist review within 1 week."
        )
    elif conflict:
        original = conflict.get("original_score", "Moderate")
        new_score = conflict.get("new_score", risk_level)
        escalation_context = (
            f"\nIMPORTANT CONTEXT: This person's risk was recently updated. "
            f"Their initial profile indicated {original} risk. After uploading their {doc_label}, "
            f"VERA re-assessed and updated the risk to {new_score}. "
            f"The greeting MUST acknowledge this change and specifically name the document ({doc_label}) "
            f"that triggered it. The plan steps should reflect the urgency of {new_score} risk, "
            f"not routine screening timelines."
        )
        urgency_note = (
            f"This person's risk was escalated to {new_score} based on their {doc_label}. "
            f"Action steps must be urgent, with first step within 1 week."
        )
    else:
        escalation_context = ""
        urgency_note = f"Schedule follow-up steps appropriately for {risk_level} risk over 6 weeks."

    return f"""Create a warm, personalised cancer screening follow-up plan for a real person.

{name_line}
Person profile:
{person_context}

Recommended specialist: {specialist}
{clinic_info}
Today's date: {today}.
{escalation_context}

The plan must feel personal. Reference their specific risk type ({types_text}) and their location ({location}).
Use "you" and "your" throughout. {urgency_note}

Return ONLY this JSON. No markdown:
{{
  "greeting": "1-2 warm sentences. If risk was escalated, acknowledge the specific document ({doc_label}) that changed the picture and what it means. Otherwise acknowledge their specific situation. Reference their name if given. No em dashes.",
  "follow_up_plan": [
    {{
      "date": "YYYY-MM-DD",
      "action": "Specific, actionable step. Reference the specialist type and their specific cancer risk.",
      "location": "Clinic or hospital name if relevant, else null",
      "contact": "Phone number if available, else null"
    }}
  ],
  "reminder_schedule": [
    {{
      "date": "YYYY-MM-DD",
      "message": "Short, warm reminder that feels personal to this person. No em dashes."
    }}
  ]
}}

Include 3 to 4 follow-up steps. Include 3 reminder messages at key moments."""


def family_messages_prompt(
    person_context: str, risk_level: str, types_text: str, clinic_name: str
) -> str:
    return f"""Draft a short, warm message for a {person_context} to send to a trusted family member or close friend asking for support.

Context: They have {risk_level.lower()} risk for {types_text} and need to book a free cancer screening at {clinic_name}.

The message should:
- Be 2 to 3 sentences
- Feel natural, not medical or clinical
- Explain they are taking a positive health step
- Ask for support or accompaniment in a gentle way
- Not mention cancer in an alarming way

Return ONLY this JSON. No markdown:
{{
  "en": "Natural English message (2-3 sentences, no em dashes)",
  "hi": "Natural Hindi message in Devanagari script (2-3 sentences)",
  "ta": "Natural Tamil message in Tamil script (2-3 sentences)"
}}"""


def checkin_prompt(name_clause: str, risk_level: str, next_action: str) -> str:
    return (
        f"You are VERA, a warm health AI companion. "
        f"It has been 3 days since{name_clause} you completed your cancer risk assessment showing {risk_level} risk. "
        f"Your next step was to: {next_action}. "
        f"Write a warm, brief 2-sentence proactive check-in message asking how they are doing and whether they have been able to take that step. "
        f"Do not repeat the full plan. Be warm and personal. No em dashes."
    )


def chat_prompt(
    user_name: str,
    risk_score: str,
    doc_type: str,
    doc_explanation: str,
    risk_reasoning: str,
    message: str,
) -> str:
    context_parts = [
        "You are VERA, a warm and caring health AI companion.",
        f"User: {user_name or 'the user'}. Current risk level: {risk_score}.",
    ]
    if doc_explanation:
        context_parts.append(
            f"The user has uploaded a {doc_type}. Here is the plain-language explanation:\n{doc_explanation}"
        )
    if risk_reasoning:
        context_parts.append(f"Risk reasoning: {risk_reasoning}")

    context_parts += [
        "Answer the user's question based on the above context.",
        "Rules: be warm and specific, never diagnose, no em dashes, 3-5 sentences unless more detail is needed.",
        f"User question: {message}",
    ]
    return "\n\n".join(context_parts)
