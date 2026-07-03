"""
Prompt templates for the Risk Profiler Agent (Agent 1).

Every prompt has a version tag. Bump the tag whenever the prompt text changes
in a way that could alter model output — the version is stored alongside each
generated risk assessment so any historical score can be traced back to the
exact prompt that produced it.
"""

# v2: assessment is anchored to published screening guidance (USPSTF, UK NSC,
# WHO) instead of unstated heuristics. NOTE: this rubric has NOT been reviewed
# by a clinician yet — sign-off is an open gate before it can be presented as
# clinically validated.
ASSESS_PROMPT_VERSION = "v2"
# v2: Verdict B's example "reason" contained sample clinical claims ("Given your
# family history and screening gap...") that the model could parrot for people
# with no such history. Reasons are now placeholder-instructed and explicitly
# restricted to findings and risk factors actually present in the input.
RECONCILE_PROMPT_VERSION = "v2"
SUMMARY_PROMPT_VERSION = "v1"
NEXT_QUESTION_PROMPT_VERSION = "v1"


def assess_prompt(full_profile: str) -> str:
    return f"""Assess cancer screening risk for the following patient profile and return structured JSON.

Patient profile:
{full_profile}

Return ONLY valid JSON — no prose, no markdown fences:
{{
  "risk_level": "Moderate",
  "risk_score": 6,
  "cancer_types_flagged": [""],
  "screening_gap_years": 4,
  "reasoning": "One sentence explaining the primary risk factors for this specific person.",
  "recommendations": "One sentence on the most urgent recommended next step for this person."
}}

Rules:
- risk_level must be exactly one of: Low, Moderate, High, Urgent
- Base your assessment on published screening guidance, not intuition. Anchors:
  - Colorectal: screening from age 45 to 75 (USPSTF 2021); a first-degree family history warrants earlier and more frequent screening
  - Breast: mammography every 2 years, ages 40 to 74 (USPSTF 2024)
  - Cervical: screening ages 21 to 65 (USPSTF 2018 / WHO); HPV vaccination lowers risk
  - Lung: annual low-dose CT for ages 50 to 80 with a 20+ pack-year smoking history (USPSTF 2021)
  - Prostate: individualized decision, ages 55 to 69 (USPSTF 2018)
- Flag High or Urgent if the person has a family history of a cancer type AND is overdue for that cancer's screening by more than 3 years
- Reserve Urgent for time-sensitive combinations (e.g. active concerning symptoms plus major risk factors)
- cancer_types_flagged must reflect this person's actual risk factors (age, gender, family history, smoking); do not list cancer types unrelated to this person's profile
- reasoning must reference only risk factors actually present in the profile above
- This is for health awareness only, not clinical diagnosis"""


def reconcile_prompt(
    profile_context: str,
    original_score: str,
    original_reasoning: str,
    signals_text: str,
) -> str:
    return f"""Compare a person's original cancer risk profile against new clinical signals from an uploaded medical document. Decide whether the new findings change the risk level.

Person profile:
{profile_context}

Original risk level: {original_score}
Original clinical reasoning: {original_reasoning or 'Not available'}

New clinical signals from uploaded document:
{signals_text}

Consider this person's specific risk factors (age, gender, family history, smoking history) when evaluating whether the new signals are clinically significant for them. A high-severity finding in someone with a family history of that cancer type should carry more weight than in someone with no such history.

Output ONE of three verdicts as valid JSON only — no prose, no markdown:

Verdict A — signals confirm original (use when severity is low and no urgency):
{{"final_score": "{original_score}", "conflict": false, "message": "Your report findings are consistent with your existing risk profile."}}

Verdict B — signals escalate risk (use when severity is high OR urgency_flag is true AND consistent with this person's risk profile):
{{"final_score": "High", "conflict": true, "reason": "<2-3 short plain sentences, addressed to the person as 'you', explaining why the report findings raise their risk level>", "message": "I've updated your risk assessment based on your report."}}

Verdict C — mixed or uncertain signals (use when confidence is below 0.6 or signals are ambiguous given this person's profile):
{{"final_score": "{original_score}", "conflict": true, "uncertain": true, "reason": "Your report contains some findings that need a specialist to review. I can not be certain whether they change your overall risk level.", "message": "I have noted some findings in your report that warrant a specialist follow-up."}}

Rules for the Verdict B "reason" text:
- Reference ONLY findings listed in the clinical signals above and risk factors actually present in this person's profile.
- Never mention family history, screening gaps, smoking, or symptoms unless they appear in the profile above. Inventing a risk factor the person does not have is a serious safety error.
- Plain language, warm and calm, no em dashes, never a diagnosis.

Return ONLY the JSON object."""


def summary_prompt(
    name_line: str,
    person_context: str,
    reasoning: str,
    risk_level: str,
    types_text: str,
) -> str:
    return f"""You are VERA, a warm and caring health companion. Write 2-3 sentences in plain, conversational language to explain a cancer risk assessment to a person.

{name_line}
Person: {person_context}.
Medical assessment: {reasoning}
Risk level: {risk_level}. Cancer types to be aware of: {types_text}.

Rules:
- Address the person directly as "you" and "your" throughout
- Reference their actual profile (age, smoking, family history) to make it feel personal and relevant
- Explain what {risk_level} risk means in everyday language — no medical jargon
- End with one genuinely encouraging sentence: a concrete, free action is available
- Never diagnose. Never say "you have cancer." Never alarm unnecessarily.
- Maximum 3 sentences. No em dashes."""


def next_question_prompt(
    question_number: int,
    max_questions: int,
    gender: str,
    age_group: str,
    bmi_text: str,
    location: str,
    prev_text: str,
    gender_note: str,
) -> str:
    return f"""You are VERA, a caring health companion. Generate question #{question_number} of {max_questions} for a cancer risk assessment.

Patient profile:
- Gender: {gender}
- Age group: {age_group}
- BMI: {bmi_text}
- Location: {location}

Previous assessment answers:
{prev_text}

Rules:
- Write in VERA's warm, direct voice using "you"/"your"
- Do NOT repeat any already-answered topic
- Do NOT repeat the same question or topic again
- Do NOT use any greetings like Hi! or Hi there in the question
- Cover: family cancer history, last screening, smoking, alcohol, physical activity, or gender/age-specific screenings{gender_note}
- If this IS question {max_questions}: open-ended health concerns, type=text, optional=true, options=[]
- Otherwise: type=choice, 3-5 short clear options

Return ONLY valid JSON (no markdown fences, no explanation):
{{
  "id": "q{question_number}",
  "question": "Warm question text here?",
  "type": "choice",
  "key": "snake_case_key",
  "options": [{{"value": "val", "label": "Label"}}],
  "optional": false,
  "why_we_ask": "One sentence explaining why this matters for cancer risk."
}}"""
