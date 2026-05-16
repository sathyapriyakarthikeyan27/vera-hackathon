# PRD — VERA: Vital Early Risk Advisor

## Problem Statement

600 million women worldwide skip cancer screenings every year. In India alone, 70% of cervical cancer cases are detected at Stage 3 or 4 — when survival odds drop sharply. The barriers are not medical. They are informational, social, financial, and systemic:

- No personalized understanding of their own risk
- Stigma and lack of family support
- Unawareness of free government schemes
- No guidance in their own language
- No one following up

VERA is the AI companion that closes this gap.

## Target Users

**Primary**: Women aged 25–60 in India and globally, with limited prior cancer screening history.

**Secondary**: Women who have had one screening but dropped off — VERA re-engages them.

**Out of scope (v1)**: Men, post-diagnosis support, clinical decision support for providers.

## User Journey

```
Woman opens VERA
        ↓
Companion Agent greets her (in her language)
        ↓
Risk Profiler asks 8 conversational questions
        ↓
Risk score + visual timeline generated
        ↓
Scheme Navigator matches her to free programs + nearby clinics
        ↓
Education Agent generates personalized animated explainer
        ↓
Companion Agent saves her profile, sets follow-up reminders
        ↓
Family message drafted on her behalf
        ↓
She leaves knowing her risk, her options, and her next step
```

## Agent Requirements

### 1. Risk Profiler Agent

**Purpose**: Assess personalized cancer risk through natural conversation.

**Input**: 8 questions covering:
- Age
- Family history of cancer (first-degree relatives)
- Date of last screening (Pap smear, mammogram, etc.)
- HPV vaccination status
- Lifestyle factors (smoking, alcohol, BMI category)
- Symptoms (if any — not diagnostic, awareness only)
- Location (country/state)
- Preferred language

**Output**:
- Cancer risk score (Low / Moderate / High / Urgent) for cervical, breast, ovarian
- Visual screening timeline showing missed windows
- Plain-language explanation of what the score means
- Disclaimer: not a diagnosis, see a doctor

**Models**: Gemini (conversation, reasoning) + MedGemma (medgemma-4b-it, medical risk calibration)

**Acceptance criteria**:
- Completes in under 90 seconds of user time
- Never uses clinical jargon without plain-language explanation
- Always shows disclaimer before displaying risk level

---

### 2. Scheme Navigator Agent

**Purpose**: Match the user to real, actionable government health programs and nearby free screening facilities.

**Input**: User location (state/district), risk profile output, income level (optional)

**Output**:
- List of matched government schemes (India: Ayushman Bharat, state programs; global: country-appropriate equivalents)
- 3 nearest clinics/hospitals offering free cancer screening
- For each clinic: distance, female doctor availability, cost, appointment link or phone
- Sorted by: proximity, then female doctor availability

**Data sources**:
- Synthetic scheme and clinic data (India priority) — mocked, no real government APIs called
- Gemini for scheme description, eligibility summarization, and "why this matches you" blurbs
- Location resolved via user input

**Acceptance criteria**:
- Shows at least 1 matched government scheme
- Shows at least 3 nearby facilities
- Clearly marks cost as Free vs. Subsidized vs. Paid
- Female doctor availability flagged prominently

---

### 3. Education Agent

**Purpose**: Generate a personalized animated explainer video that reduces fear and increases understanding.

**Input**: Risk profile, language preference, cancer type(s) flagged in risk score

**Output**:
- Short animated explainer video (60–90 seconds) covering:
  - What the screening involves (BSE, Pap smear, mammogram)
  - What to expect before, during, after
  - Why early detection matters for her specific risk level
- Plain-language text summary (same content, accessible without video)

**Constraints**:
- NO live camera — animated only
- Personalized to her risk type and language
- Culturally appropriate visuals

**Models**: Gemini (script generation, personalization) + animation pipeline (TBD — static frames or pre-rendered segments for demo)

**Acceptance criteria**:
- Video plays without errors in demo
- Content matches the user's risk profile (not generic)
- Text summary always shown as fallback

---

### 4. Companion Agent

**Purpose**: Be VERA's persistent, warm presence — remembering the user across sessions and helping her take the next step.

**Input**: Full session context from the 3 other agents, language preference, user name (optional)

**Output**:
- Personalized follow-up plan (what to do, by when)
- Screening reminder schedule (configurable: 1 week, 1 month, 3 months)
- Family message draft — a ready-to-send message to a family member framing the appointment as routine self-care
- Multilingual support: English, Tamil, Hindi

**Memory**: Session data persisted — when user returns, VERA greets her by name and recalls her last interaction.

**Models**: Gemini (multilingual generation, memory summarization)

**Acceptance criteria**:
- Returns user correctly identified on second visit in demo
- Family message draft is warm, non-clinical, culturally appropriate
- Follow-up plan is specific (date, action, location)

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Demo reliability | 100% — no crashes during 7-minute demo |
| Response latency | < 3 seconds per agent step |
| Multilingual | English, Tamil, Hindi |
| Mobile responsive | Yes — primary access is mobile |
| Accessibility | High contrast, readable font sizes |
| Privacy | No PII stored beyond demo session |
| Disclaimers | Shown at every risk output |

## Out of Scope (v1 / Hackathon)

- Live doctor consultation
- Actual appointment booking
- EHR integration
- Post-diagnosis support
- Male health screening
- Real-time geolocation tracking
- Native mobile app
- Actual video rendering pipeline (demo uses pre-rendered segments)
