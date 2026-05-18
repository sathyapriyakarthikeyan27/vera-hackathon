"""
Health questions for the Risk Profiler adaptive chat.
Name, age, gender, location, and language are collected at sign-up — not here.
"""

QUESTIONS: list[dict] = [
    {
        "id": "q1",
        "question": "Has anyone in your immediate family (a parent, sibling, or child) ever been diagnosed with cancer?",
        "type": "choice",
        "key": "family_history",
        "placeholder": "",
        "options": [
            {"value": "yes_breast_ovarian", "label": "Yes, breast or ovarian cancer"},
            {"value": "yes_cervical", "label": "Yes, cervical cancer"},
            {"value": "yes_colorectal", "label": "Yes, colorectal cancer"},
            {"value": "yes_other", "label": "Yes, another type"},
            {"value": "no", "label": "Not that I know of"},
        ],
    },
    {
        "id": "q2",
        "question": "When did you last have a cancer screening, like a Pap smear, mammogram, or colonoscopy?",
        "type": "choice",
        "key": "last_screening",
        "placeholder": "",
        "options": [
            {"value": "within_1yr", "label": "Within the last year"},
            {"value": "1_3yr", "label": "1 – 3 years ago"},
            {"value": "3_5yr", "label": "3 – 5 years ago"},
            {"value": "over_5yr", "label": "More than 5 years ago"},
            {"value": "never", "label": "I've never had one"},
        ],
    },
    {
        "id": "q3",
        "question": "Have you received the HPV vaccine?",
        "type": "choice",
        "key": "hpv_vaccine",
        "placeholder": "",
        "options": [
            {"value": "yes", "label": "Yes, I have"},
            {"value": "no", "label": "No, I haven't"},
            {"value": "unsure", "label": "I'm not sure"},
        ],
    },
    {
        "id": "q4",
        "question": "Do you currently smoke, or have you smoked regularly in the past?",
        "type": "choice",
        "key": "smoking",
        "placeholder": "",
        "options": [
            {"value": "current", "label": "Yes, currently"},
            {"value": "former", "label": "Used to, but stopped"},
            {"value": "never", "label": "No, never"},
        ],
    },
    {
        "id": "q5",
        "question": "Is there anything that's been worrying you health-wise lately? This is completely optional.",
        "type": "text",
        "key": "symptoms",
        "placeholder": "Describe any symptoms or concerns, or tap Skip",
        "options": [],
        "optional": True,
    },
]


def format_question(q: dict, answers: dict | None = None) -> dict:
    """Interpolate collected answers into question text (e.g. {user_name})."""
    text = q["question"]
    if answers and "{" in text:
        safe = {k: (v or "") for k, v in answers.items() if v is not None}
        try:
            text = text.format_map(_SafeDict(safe))
        except Exception:
            pass
    return {**q, "question": text}


class _SafeDict(dict):
    """Returns the key placeholder unchanged if the key is missing."""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
