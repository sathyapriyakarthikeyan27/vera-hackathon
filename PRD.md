# PRD — VERA: Vital Early Risk Advisor

## Problem Statement

Hundreds of millions of people worldwide skip cancer screenings every year. In India, 70% of cervical cancer cases are detected at Stage 3 or 4 — when survival odds drop sharply. The barriers are not medical. They are informational, social, financial, and systemic:

- No personalised understanding of their own risk
- Unawareness of free government schemes
- No guidance on which specialist to see
- No one following up after a screening recommendation
- Medical documents explained in jargon instead of plain language

VERA is the AI companion that closes this gap — for everyone.

## Target Users

**VERA is for everyone.** Any age, any gender, any location. Cancer risk is universal.

**Primary**: Adults aged 25 to 65 with no recent cancer screening history or with uploaded medical documents they need explained.

**Secondary**: People who received a risk score and need help navigating next steps (specialist, scheme, care plan).

**Out of scope (demo)**: Post-diagnosis clinical support, real-time appointment booking, live camera.

---

## User Journey

```
User opens VERA
        ↓
Signup: Name, DOB, Gender, Location, Height, Weight
(Frontend computes age_group from DOB, BMI from height+weight)
        ↓
Agent 1 — Initial Assessment
AI-generated adaptive questions (up to 6, one at a time, card UI)
Risk scored: Low / Medium / High
Plain-language reasoning shown
        ↓
Agent 2 — Care Navigation
Government scheme matched (Ayushman Bharat, NHS, NHIA)
Specialist type identified
Nearest facilities shown
        ↓
[Optional] User uploads medical document
        ↓
Agent 3 — Records Explainer (dual output)
  Output 1: Plain-language explanation shown to user
  Output 2: Clinical signals written to pending_signals
        ↓
Router detects pending_signals → Agent 1 (reconcile mode)
        ↓
If conflict detected:
  Conflict card shown — old score vs new score, plain-language reason
  Agent 2 re-activates with updated risk
        ↓
Agent 4 — Companion
  /chat: Q&A about the uploaded document and risk profile
  /companion/checkin: "Simulate 3 Days Later" proactive check-in
  /companion/followup: Structured follow-up plan
```

---

## Agent Requirements

### Agent 1 — Risk Profiler

**Purpose**: Score cancer risk through adaptive AI-generated questions. Also reconcile new clinical evidence from uploaded documents.

**Inputs**:
- Signup profile: name, age_group, gender, location, height_cm, weight_kg, BMI
- AI-generated question answers: family history, conditions, lifestyle, screening history, symptoms
- Pending signals from Agent 3 (reconcile mode only)

**Outputs**:
- Risk level: `low` | `medium` | `high`
- Plain-language reasoning (why VERA gave that score)
- Visual screening timeline
- In reconcile mode: conflict verdict (Agreement / Escalation / Uncertainty)

**Question types**: `choice` (auto-advance on click), `text` (textarea + Skip)

**Models**: Gemini 2.5 Flash

**Acceptance criteria**:
- Questions are contextual to gender, age, BMI, location, prior answers
- Risk output always includes plain-language reasoning
- Reconciler produces correct conflict verdict when signals contradict profile score

---

### Agent 2 — Care Navigator

**Purpose**: Match user to a government scheme and a specialist based on risk level and location.

**Inputs**: Session ID (reads risk score, cancer types flagged, location from session)

**Outputs**:
- Matched government schemes with plain-language eligibility summary
- Specialist type with reasoning (Gastroenterologist, Oncologist, Pulmonologist, etc.)
- Nearest clinics / hospitals (synthetic data from pgvector RAG)

**Data**: All scheme and clinic data is synthetic JSON stored in pgvector. No real government APIs are called. This is a deliberate decision.

**Models**: Gemini 2.5 Flash + `models/embedding-001` (pgvector similarity search)

**Acceptance criteria**:
- Always returns at least one matched scheme
- Specialist type is specific (not just "see a doctor")
- Output is location-aware

---

### Agent 3 — Records Explainer

**Purpose**: Read uploaded medical documents and produce dual output — plain-language explanation for the user and structured clinical signals for Agent 1.

**Supported file types**: PDF, JPG, PNG (lab reports, MRI scans, pathology reports, colonoscopy reports)

**Outputs**:

1. Plain-language explanation:
   - What the document is
   - Key findings in plain language
   - Anything needing attention, stated calmly
   - What to do next
   - Disclaimer: "Please discuss findings with your doctor"

2. Clinical signals JSON:
   ```json
   {
     "anomalies": ["specific finding"],
     "severity": "high" | "medium" | "low",
     "confidence": 0.0-1.0,
     "specialist_signal": "Specialist type" | null,
     "urgency_flag": true | false
   }
   ```

**Privacy**: Files processed from bytes in memory. Never written to disk. Never stored after response. Always use try/finally to guarantee cleanup.

**Models**: Gemini 2.5 Pro (multimodal — handles all document types including images)

**Acceptance criteria**:
- Plain-language explanation contains no unexplained jargon
- Clinical signals JSON is valid and specific
- Signals correctly trigger reconcile flow via pending_signals

---

### Agent 4 — Companion

**Purpose**: Proactive health companionship. Powers chat, follow-up plans, and proactive check-ins.

**Endpoints**:

- `POST /companion/chat` — Q&A using actual session context (records explanation, risk score, reasoning). Real-time, not static.
- `POST /companion/followup` — Structured follow-up plan (next action, specialist, scheme, reminder schedule).
- `POST /companion/checkin` — Simulates a proactive 3-days-later check-in from VERA.

**Context used**: records_output (document explanation), risk_assessment (score, reasoning), risk_profile (risk level, plain-language summary), user_name.

**Models**: Gemini 2.5 Flash

**Acceptance criteria**:
- Chat answers are specific to the user's actual uploaded document
- Check-in message is personalised to the user's next action
- No em dashes in any output

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Demo reliability | 100% — no crashes during 7-minute demo |
| Response latency | Under 5 seconds per agent step |
| Accessibility | WCAG 2.1 AA — 44px touch targets, 16px min font, 4.5:1 contrast |
| Mobile responsive | Yes — primary access may be mobile |
| Privacy | Health records never stored; processed in memory only |
| Disclaimers | Shown at every risk output |
| No em dashes | In any user-facing content |

---

## Scope Cuts (Do Not Reintroduce)

| Cut | Reason |
|-----|--------|
| Full authentication | Not yet implemented; localStorage session is the current state (roadmap item) |
| i18n / multilanguage | Not yet active; English hardcoded (roadmap item) |
| MedGemma / Featherless | Gemini 2.5 Pro currently handles records and image analysis |
| Gemini Vision | Gemini 2.5 Pro handles all document types including images |
| Real government APIs | Scheme/hospital data is synthetic via RAG; real APIs need per-country partnerships |
| Celery / external task queue | FastAPI BackgroundTasks covers scheduling. Redis IS used, but only as a cache layer |
| LangChain | Raw async Python simpler and more debuggable |
| Live appointment booking | Hospital booking APIs are fragmented and unreliable |
| Native mobile app | PWA is installable on mobile, single codebase, no app store review |

---

## Design Principles

1. **No passwords, no jargon, no em dashes.** These three constraints serve the same user: someone anxious about their health who needs to trust VERA immediately.
2. **VERA speaks in first person.** "I", "I've found", "I'm here." Not a system. A companion.
3. **Plain language everywhere.** Never use a medical term without a plain-language explanation alongside it.
4. **WCAG 2.1 AA.** 44px touch targets, 16px minimum body font, visible focus indicators, meaningful alt text.
5. **Deterministic router.** Never replace with an LLM-based planner. Deterministic equals reliable, low-latency, predictable in production.
6. **Agent 1 owns score.** No other agent writes to `risk_assessment.score`. This prevents race conditions.
