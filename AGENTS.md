# AGENTS — VERA Agent Specifications

## Agent Orchestration Model

VERA uses a deterministic router to dispatch incoming requests to the correct agent. No LLM decides routing — the conditions are code.

```
Deterministic Router
  ├── user.is_new            → Agent 1 (initial profiling)
  ├── file_uploaded          → Agent 3 (records + signal extraction)
  ├── scheduled_trigger      → Agent 4 (proactive check-in)
  ├── pending_signals        → Agent 1 (reconcile mode)
  └── default                → Agent 2 (care navigation)
```

All agents share state through a single session object in PostgreSQL. Agent 1 is the only agent that writes to `risk_assessment.score`. All other agents write to `pending_signals`.

---

## Agent 1: Risk Profiler

### Purpose
Score cancer risk from the user's profile using AI-generated adaptive questions. Also runs as reconciler when Agent 3 surfaces new clinical signals.

### Two Modes

**Initial Profiling Mode** — triggered when a session is new.
- Agent 1 generates up to 6 contextual questions using Gemini, one at a time
- Each question is informed by: gender, age_group, BMI, location, and prior answers
- Questions always cover: family history, existing conditions, lifestyle (smoking/alcohol), screening history, optional symptoms

**Reconcile Mode** — triggered when `risk_assessment.pending_signals` is non-empty and `reconciled = False`.
- Agent 1 reads the existing score and all pending signals from Agent 3
- Compares original profile-based score against new clinical evidence
- Produces one of three verdicts: Agreement, Escalation (conflict), or Uncertainty (conflict)

### Question Generation

Gemini receives: gender, age_group, BMI, location, previous answers
Returns structured JSON per question:
```json
{
  "id": "q3",
  "question": "Have you had a colonoscopy in the last 5 years?",
  "type": "choice",
  "key": "colonoscopy_history",
  "options": [
    {"value": "yes", "label": "Yes"},
    {"value": "no", "label": "No"},
    {"value": "not_sure", "label": "Not sure"}
  ],
  "why_we_ask": "Colonoscopy history affects colorectal cancer risk scoring."
}
```

### Risk Scoring

Gemini Flash receives the full structured profile and returns:
```json
{
  "risk_level": "High",
  "risk_score": 8,
  "cancer_types_flagged": ["colorectal"],
  "screening_gap_years": 6,
  "plain_language_summary": "I rated your risk as high because of your family history of colorectal cancer and the fact that you have not had a colonoscopy in over 5 years.",
  "disclaimer": "This is not a medical diagnosis. VERA provides risk awareness only."
}
```

Falls back to rule-based scoring if Gemini is unavailable.

### Reconcile Output

```python
# Verdict A — Agreement
{"final_score": "medium", "conflict": False, "reasoning": "Lab findings are consistent with your profile."}

# Verdict B — Escalation (triggers conflict card)
{"final_score": "high", "conflict": True, "reasoning": "Your report shows findings that indicate higher risk than your initial profile suggested."}

# Verdict C — Uncertainty
{"final_score": "medium", "conflict": True, "uncertain": True, "reasoning": "Your report contains mixed signals. I recommend a follow-up with a specialist."}
```

### Models
- **Gemini 2.5 Flash** — question generation, risk scoring, reconciliation, plain-language summary

---

## Agent 2: Care Navigator

### Purpose
Based on the risk score and location from Agent 1, find the nearest actionable next step: government scheme, specialist, and screening facility.

### Matching Logic

```
Risk level + user location + cancer types flagged
    ↓
Vector similarity search in scheme_data (pgvector)
    ↓
Gemini summarizes eligibility in plain language
    ↓
Return: matched schemes + specialist type + nearest clinics
```

### Government Schemes (mocked via RAG in pgvector)

| Country | Scheme |
|---------|--------|
| India | Ayushman Bharat (PM-JAY) |
| Egypt | NHIA (National Health Insurance Authority) |
| UK | NHS free cancer screening programmes |

No real government APIs are called. All data is synthetic JSON embedded with pgvector for similarity search. This is a deliberate hackathon decision.

### Specialist Routing

| Signal | Specialist |
|--------|-----------|
| Colorectal / bowel symptoms | Gastroenterologist |
| Breast / gynaecologic | Gynaecologic Oncologist |
| Lung / smoking history | Pulmonologist |
| Skin changes | Dermatologist |
| General / unclear | Oncologist |

### Models
- **Gemini 2.5 Flash** — scheme description summarization, eligibility matching, plain-language output
- **Embedding model** — `models/embedding-001` (768-dimensional, v1beta compatible) for pgvector similarity search

---

## Agent 3: Records Explainer

### Purpose
Read uploaded medical documents (PDF, JPG, PNG) and produce dual output: a plain-language explanation for the user, and structured clinical signals for Agent 1.

### Dual Output

**Output 1 — User-facing explanation**
- Plain language, no jargon
- Flags anything urgent calmly
- Ends with: "This is a plain-language explanation only. Please discuss findings with your doctor."
- No em dashes

**Output 2 — Clinical signals JSON**
```json
{
  "anomalies": ["12mm tubulovillous adenoma, ascending colon, not fully resected"],
  "severity": "high",
  "confidence": 0.91,
  "specialist_signal": "Gastroenterologist",
  "urgency_flag": true
}
```

After extraction, Agent 3:
1. Appends signals to `risk_assessment.pending_signals`
2. Sets `risk_assessment.reconciled = False`
3. Router sees pending signals and routes to Agent 1 reconciler

### Privacy
Files are read from bytes in memory. Never written to disk. Never stored after response.

```python
# Privacy pattern shown to judges
content: bytes = await file.read()
# ... process in memory ...
# file bytes go out of scope — no disk write, no storage
```

### Models
- **Gemini 2.5 Pro** — document analysis, clinical signal extraction, multimodal (PDF, JPG, PNG)

---

## Agent 4: Companion

### Purpose
Proactive health companionship. VERA reaches out — users do not have to remember to come back. Also powers the `/chat` page for report Q&A.

### Endpoints

**`POST /companion/chat`** — Real-time Q&A based on the user's uploaded records and risk profile. Gemini Flash receives the full session context (records explanation, risk score, risk reasoning) and responds to the user's specific question.

**`POST /companion/followup`** — Generates a structured follow-up plan: next action, specialist referral, scheme to use, reminder schedule.

**`POST /companion/checkin`** — Demo endpoint: simulates a proactive 3-days-later check-in from VERA. Triggered by "Simulate 3 Days Later" button in the UI.

### Memory
Check-in conversations are stored in `checkin_memory` table with pgvector embeddings (768-dimensional). Used to personalise future messages.

### Models
- **Gemini 2.5 Flash** — all companion output: chat replies, follow-up plans, check-in messages

---

## The Collaboration Mechanic — Conflict Detection

This is the centrepiece of VERA's multi-agent architecture.

```
1. Agent 1 scores MEDIUM from profile alone
        ↓
2. User uploads colonoscopy report
        ↓
3. Agent 3 reads report: anomalies found, severity=HIGH
   → writes to pending_signals, sets reconciled=False
        ↓
4. Router sees pending_signals → Agent 1 (reconcile mode)
        ↓
5. Agent 1 compares: original=MEDIUM vs signal=HIGH
   → CONFLICT DETECTED
   → writes: score=high, conflict={original, new, reason}
        ↓
6. Conflict card shown to user:
   "I've updated your assessment from Medium to High based on your report."
        ↓
7. Agent 2 activates with HIGH risk
   → Gastroenterologist + urgent scheme
```

No agent overwrites `score` except Agent 1. This is enforced by design, not by runtime checks.

---

## Shared Risk Assessment Object

```python
risk_assessment = {
    "score": "low" | "medium" | "high",   # Agent 1 owns this
    "confidence": 0.0-1.0,
    "reasoning": str,                      # plain-language explanation
    "source": "profile_only" | "profile+records",
    "pending_signals": [],                 # Agent 3 writes here only
    "reconciled": bool,
    "conflict": None | {
        "original_score": str,
        "new_score": str,
        "reason": str,
        "shown_to_user": bool
    }
}
```
