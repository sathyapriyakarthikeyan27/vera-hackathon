# VERA — Claude Code Context File
**Vital Early Risk Advisor**
Last updated: May 16, 2026

---

## What You Are Building

A proactive cancer risk advisor with 4 specialised agents that collaborate through shared state. Not a symptom checker. Not a generic health app. A focused system that catches cancer risk before it becomes a crisis.

**VERA is for everyone — any age, any gender, any location.** Do not frame VERA as a women's health app. Cancer risk is universal.

---

## VERA's Voice — Apply Everywhere

All user-facing content must sound like VERA speaking directly to the person. Not a system. Not a product. A caring, knowledgeable companion.

- **First person:** "I", "me", "I'll", "I've found", "I'm here"
- **Second person:** Address as "you" — never "the user", never "patients"
- **Tone:** Warm, unhurried, never clinical or alarming
- **Style:** Short sentences. Plain language. No jargon.
- **Confidence without preaching:** VERA informs — never lectures
- **No "truth" framing:** Do not use phrases like "the truth about your health". VERA is caring, not confrontational.

This applies to: landing page, signup, chat, risk output, conflict card, companion messages, education content, scheme navigator output.

**Hackathon:** AI Agent Olympics — Milan AI Week 2026
**Platform:** lablab.ai
**Track:** Collaborative Agent Swarms
**Primary Partner:** Google Gemini (competing for Gemini prize)
**Secondary Partner:** Vultr (deployment)
**Submission deadline:** May 19, 5PM
**Live demo:** May 20, Milan

> ⚠️ **REVISED TIMELINE — May 16 update**
> All feature development must be complete by end of **May 17 (tomorrow)**.
> May 18 = full demo run + Vultr deployment only. May 19 = polish + submit. No new features after May 17.

---

## The Four Agents

| Agent | Name | Role |
|---|---|---|
| Agent 1 | Risk Profiler | Scores cancer risk from user profile. Also runs as reconciler when new clinical signals arrive. |
| Agent 2 | Care Navigator | Finds nearest specialists, government schemes, screening camps based on risk score. |
| Agent 3 | Records Explainer | Reads uploaded lab reports/MRIs. Explains in plain language AND extracts structured clinical signals for Agent 1. |
| Agent 4 | Companion | Proactive check-ins, medication reminders, follow-up appointment reminders. |

---

## Onboarding Flow

### Signup — Minimal Friction
Collect only four fields. Do not ask anything else at this stage.

```
Name | Age | Gender | Location
```

### First Session — Adaptive Profiling (Agent 1)
After signup, Agent 1 runs a conversational onboarding. Questions adapt based on age and gender. It must feel like a conversation, not a form.

**Always ask:**
- BMI (height + weight, calculate silently)
- Family history of cancer (which type, which relative)
- Existing medical conditions

**Ask only if relevant to age/gender:**
- Cervical screening history → people with a cervix, 25+
- Mammogram history → people with breasts, 40+
- Prostate screening → men / AMAB, 50+
- Colonoscopy history → anyone 45+ or with family history of colorectal cancer
- Smoking / alcohol / tobacco use → all adults
- Current medications → only if they mention a chronic condition

**Symptoms — optional, never mandatory:**
- Surface a single open field: *"Are you experiencing anything that's been worrying you?"*
- If symptoms are entered, escalate urgency in the risk score output
- VERA is preventive — most users are pre-symptom. Do not make symptoms feel required.

**Tone:** Warm, human, one question at a time. Never show all questions at once. Use Gemini to generate the next question dynamically based on the previous answer.

---

## Core Features

### Feature 1 — Risk Advisor (Agent 1)

**Purpose:** Proactively assess cancer risk from profile data and optional symptoms. Not a symptom checker — upstream of symptoms.

**Inputs:** User profile (age, gender, BMI, family history, conditions, medications, symptoms if provided)

**Output:** Risk level — `low` | `medium` | `high`

**Behaviour by risk level:**

| Risk Level | Action |
|---|---|
| Low | Education content + periodic check-in scheduled via Agent 4 |
| Medium | Screening recommendation + Agent 2 activated |
| High | Urgent specialist referral + Agent 2 activated immediately |
| High + symptoms present | Urgent referral flagged as time-sensitive |

**Specialist routing logic (Needs Validation):**

| Cancer Type / Signal | Specialist |
|---|---|
| Colorectal risk / bowel symptoms | Gastroenterologist |
| Breast / gynaecologic risk | Gynaecologic Oncologist or Oncologist |
| Lung / smoking history | Pulmonologist |
| Skin changes | Dermatologist |
| General / unclear | Oncologist |

**Agent 1 also runs as reconciler** — see Collaborative Architecture section.

---

### Feature 2 — Care Navigator (Agent 2)

**Purpose:** Based on risk score and specialist type from Agent 1, find the nearest actionable next step for the user.

**Outputs (in order of priority):**
1. Relevant government scheme for user's country
2. Nearest free screening camp (if medium risk)
3. Nearest reputed hospital / specialist (if high risk)
4. Specialist type — not just "see a doctor", but exactly which specialist and why

**Government schemes (mocked via RAG in pgvector — not real APIs):**

| Country | Scheme |
|---|---|
| India | Ayushman Bharat (PM-JAY) |
| Egypt | NHIA (National Health Insurance Authority) |
| UK | NHS — free cancer screening programmes |

**Filters applied:** User location, cost preference, risk urgency

**Note:** All hospital and scheme data is synthetic JSON stored in pgvector. Do not attempt to call real government APIs. This is a deliberate hackathon decision.

---

### Feature 3 — Health Records Explainer (Agent 3)

**Purpose:** Read uploaded medical documents and explain them in plain language. Also extract structured clinical signals for Agent 1 (see Collaborative Architecture).

**Supported file types:** PDF, JPG, PNG (lab reports, MRI scans, prescriptions, pathology reports)

**Model:** MedGemma reads and reasons over clinical content. Gemini Vision for image-based documents.

**Behaviour:**
- Explains findings in the user's preferred language — no medical jargon
- Flags anything that needs urgent attention explicitly
- Answers follow-up questions about the report in the same session
- Produces dual output — user explanation + clinical signals JSON (see Agent 3 section)

**Privacy:** Files processed in memory only. Deleted immediately after response via `try/finally`. Never stored. Never logged.

**What Agent 3 must NOT do:**
- Diagnose
- Tell the user they have cancer
- Contradict a doctor's report
- Store or cache the file after processing

---

### Feature 4 — Companion Agent (Agent 4)

**Purpose:** Proactive health companionship. VERA reaches out — users don't have to remember to come back.

**Behaviours:**

**Check-ins:**
- Scheduled after every significant event (new risk score, specialist referral, screening)
- Tone: warm, conversational, not clinical
- Asks one question at a time — never a checklist

**Medication reminders (post-diagnosis users):**
- Stores medication name, dosage, frequency in PostgreSQL
- FastAPI BackgroundTasks handles scheduling — no Celery, no Redis
- Reminder sent via in-app notification

**Follow-up appointment reminders:**
- Stores appointment date and specialist name
- Reminds 3 days before and day-of

**Educational content:**
- What to expect at a first oncology appointment
- How to prepare for a colonoscopy
- Breast self-examination guide
- Personalised to the user's risk type — not generic

**Persistent memory:**
- Every check-in conversation stored in pgvector
- Agent 4 builds a living health timeline per user
- Used to personalise future messages and surface patterns over time

**Demo button:** "Simulate 3 Days Later" — fast-forwards time to show a proactive check-in firing. Judges must see this. It demonstrates VERA is not a passive tool.

---

## Tech Stack

### Frontend
- Next.js 14 (PWA — mobile-first, no app store needed)
- Tailwind CSS + shadcn/ui

### Backend
- FastAPI (Python) — async
- Deterministic rule-based router — NOT LLM-based routing
- FastAPI BackgroundTasks for scheduling

### Database
- PostgreSQL — user profiles, appointments, reminders
- pgvector — vector embeddings, conversation memory, mock hospital/scheme data (RAG)

### AI Models
| Model | Purpose |
|---|---|
| Gemini 2.0 Flash | Conversations, routing, multilingual, content generation |
| MedGemma 27B (fallback: 4B) | Medical risk reasoning, records understanding |
| Gemini Vision | Reading uploaded MRI/lab report images |

### Infrastructure
- Vultr — deployment
- Vultr Object Storage — temporary health record storage, deleted immediately after response
- Docker — containerised

### Explicitly Dropped (do not reintroduce)
- ❌ LangChain
- ❌ Celery + Redis (use FastAPI BackgroundTasks)
- ❌ Real government APIs (mocked via RAG in pgvector)
- ❌ Gemini TTS (stretch goal only)

---

## Deterministic Router

```python
if user.is_new:
    route_to(Agent1)
elif payload.file_uploaded:
    route_to(Agent3)  # Agent 3 then triggers reconciliation flow
elif payload.is_scheduled_trigger:
    route_to(Agent4)
elif risk_assessment.pending_signals and not risk_assessment.reconciled:
    route_to(Agent1)  # reconciliation mode
else:
    route_to(Agent2)
```

**Important:** The router is deterministic by design. Do not replace it with an LLM-based planner. Deterministic = reliable, low-latency, demo-safe.

---

## Collaborative Architecture — The Core Feature

This is what makes VERA a collaborative agent system, not just a pipeline.

### The Shared Risk Assessment Object

Every agent reads from and writes to this shared object in PostgreSQL. Agent 1 is the **only** agent that writes the final `score`. All other agents write to `pending_signals`.

```python
risk_assessment = {
    "score": "low" | "medium" | "high",  # Agent 1 owns this field
    "confidence": 0.0–1.0,
    "source": "profile_only" | "profile+records",
    "pending_signals": [],    # Agent 3 writes here — never Agent 1
    "reconciled": bool,       # False = reconciliation needed
    "conflict": None | {      # populated when agents disagree
        "original_score": str,
        "new_score": str,
        "reason": str,
        "shown_to_user": bool
    }
}
```

**Rule:** No agent overwrites `score` directly except Agent 1. This prevents race conditions.

---

### Collaboration Mechanic 1 — Conflict Detection (Ideas 1 + 5 combined)

**The scenario:** Agent 1 scores a user as MEDIUM risk from their profile. The user later uploads a lab report. Agent 3 reads it and finds high-severity clinical signals. Agent 1 reconciles — conflict detected — score changes to HIGH. The user sees the conflict surfaced explicitly.

**Why this matters to judges:** The agents are not just passing data — they are checking each other's conclusions. A finding from one agent changes the output of another. That is genuine collaboration.

---

### Agent 3 — Dual Output (Idea 5)

Agent 3 now produces TWO outputs for every uploaded document:

**Output 1 — User-facing explanation** (existing behaviour)
Plain language summary in the user's preferred language. Flags anything urgent.

**Output 2 — Clinical signals for Agent 1** (new behaviour)

Prompt addition for Agent 3:
```
After generating the user explanation, extract clinical signals as JSON:
{
  "anomalies": ["list of findings"],
  "severity": "high" | "medium" | "low",
  "confidence": 0.0–1.0,
  "specialist_signal": "Specialist type if indicated" | null,
  "urgency_flag": true | false
}
Return ONLY valid JSON for this block. No prose. No markdown fences.
```

After extraction, Agent 3:
1. Appends extracted JSON to `risk_assessment.pending_signals`
2. Sets `risk_assessment.reconciled = False`
3. Returns to router — router sees pending signals and routes to Agent 1 reconciler

---

### Agent 1 — Reconciliation Mode (Idea 1)

Agent 1 has two modes. Check which mode to run:

```python
def get_agent1_mode(user_profile):
    ra = user_profile.risk_assessment
    if not ra["reconciled"] and len(ra["pending_signals"]) > 0:
        return "reconcile"
    return "initial_profile"
```

**Reconciliation prompt context:**
```python
reconciliation_context = {
    "original_score": risk_assessment["score"],
    "original_confidence": risk_assessment["confidence"],
    "new_clinical_signals": risk_assessment["pending_signals"],
}
```

**Agent 1 reconciler outputs one of three verdicts:**

```python
# Verdict A — Agreement (signals confirm original score)
{
    "final_score": "medium",
    "conflict": False,
    "message": "Lab findings are consistent with your existing risk profile."
}

# Verdict B — Escalation (signals contradict original score)
{
    "final_score": "high",
    "conflict": True,
    "reason": "Your lab report shows findings that indicate higher risk than your initial profile suggested."
}

# Verdict C — Uncertainty (signals are mixed)
{
    "final_score": "medium",
    "conflict": True,
    "uncertain": True,
    "reason": "Your report contains mixed signals. VERA recommends a follow-up to clarify."
}
```

After reconciliation:
- Write `final_score` to `risk_assessment.score`
- Write conflict object to `risk_assessment.conflict`
- Set `risk_assessment.reconciled = True`
- Clear `risk_assessment.pending_signals`
- If `conflict = True` → surface conflict message to user before routing to Agent 2

**Verdict C is impressive to judges.** VERA admitting uncertainty is more credible than always being confident. Do not skip it.

---

### What the User Sees on Conflict

When `conflict = True`, show this before the care navigation output:

> *"VERA has updated your risk assessment. Your initial profile suggested [ORIGINAL SCORE] risk, but your [document type] has changed this picture. VERA now considers your risk [NEW SCORE]. Here's why: [REASON]. Here's what to do next."*

This moment is your headline demo beat. Make it visually distinct in the UI — a different card, a different colour, not just a text update.

---

## Full Collaboration Flow (Demo Sequence)

```
1. New user signs up
         ↓
2. Agent 1 (initial mode)
   → Adaptive onboarding questions
   → Scores risk: MEDIUM
   → Writes to risk_assessment: score=medium, source=profile_only
         ↓
3. Agent 2 activates
   → Shows medium-risk recommendation (screening, not urgent referral)
         ↓
4. User uploads colonoscopy report
         ↓
5. Agent 3 (dual output)
   → Explains report to user in plain language
   → Extracts: {anomalies: ["abnormal polyp"], severity: "high", urgency_flag: true}
   → Writes to pending_signals
   → Sets reconciled = False
         ↓
6. Router sees pending_signals → routes to Agent 1 (reconcile mode)
         ↓
7. Agent 1 (reconcile mode)
   → Original: MEDIUM | New signal: HIGH
   → CONFLICT DETECTED
   → Writes: score=high, conflict={original: medium, new: high, reason: "..."}
         ↓
8. User sees conflict card:
   "VERA has updated your assessment from MEDIUM to HIGH based on your report."
         ↓
9. Agent 2 activates with HIGH risk
   → Nearest Gastroenterologist
   → Ayushman Bharat / NHIA / NHS scheme shown
```

---

## Privacy Architecture

- Health records never stored — processed in memory, deleted immediately after response
- Use explicit `try/finally` block for file deletion — **show this code to judges**
- User profile encrypted at rest
- No PII in logs
- Session-based processing for all medical documents
- In-app disclaimer: *"VERA is a health awareness tool, not a medical device"*

```python
# Show judges this pattern
async def process_health_record(file):
    temp_path = save_temporarily(file)
    try:
        result = await medgemma.analyze(temp_path)
        return result
    finally:
        os.remove(temp_path)  # always deleted, even on exception
```

---

## Multilingual Support

- Full app in user's preferred language
- Priority: English, Tamil, Hindi, Arabic
- Powered by Gemini's multilingual capability
- All Agent 3 explanations and Agent 1 conflict messages must respect `user.preferred_language`

---

## Demo Personas - Needs validation

**Persona 1 — Primary demo persona**
45-year-old male, smoker, family history of colorectal cancer
→ Initial score: MEDIUM
→ Uploads colonoscopy report with abnormal finding
→ Conflict fires → score becomes HIGH
→ Agent 2 routes to Gastroenterologist + Ayushman Bharat

**Persona 2**
38-year-old woman, family history of breast cancer, no prior screening
→ Score: HIGH from profile alone
→ Agent 2 routes to Oncologist
→ No conflict scenario — straight path demo

**Persona 3 — Post-diagnosis**
User on chemotherapy
→ Agent 4 demo — medication reminders + follow-up
→ "Simulate 3 Days Later" button

---

## Demo Flow (7 Minutes)

| Minute | What Happens |
|---|---|
| 0:00–0:30 | New user signs up — name, age, gender, location |
| 0:30–1:30 | Adaptive onboarding questions — feels conversational |
| 1:30–2:00 | Risk profile generated — MEDIUM — visual output |
| 2:00–3:00 | Agent 2 shows government scheme + nearest specialist |
| 3:00–4:30 | Upload lab report — Agent 3 explains → conflict fires → HIGH → new care plan |
| 4:30–5:00 | Conflict card shown to user — the collaboration moment |
| 5:00–5:30 | "Simulate 3 Days Later" — Agent 4 proactive check-in |
| 5:30–6:00 | Post-diagnosis persona — medication reminder demo |
| 6:00–7:00 | Q&A buffer |

**The conflict card at 4:30 is the centrepiece of the demo. Everything else supports it.**

---

## Build Order (Revised — everything done by May 17)

| Day | Date | Status | Focus |
|---|---|---|---|
| Day 2 | May 15 | ✅ Done | `risk_assessment` schema + Agent 1 initial profiling + MedGemma risk scoring |
| Day 3 | May 16 | ✅ Done | Signup flow + DB bootstrap fix + Agent 1 reconcile mode + questions restructured |
| Day 4 | May 17 | 🔴 **TODAY — MUST FINISH** | Agent 3 dual output + conflict detection + Agent 2 care nav + Agent 4 companion + conflict card UI |
| Day 5 | May 18 | 🔒 Deploy only | Full demo run + Vultr deployment — NO new features |
| Day 6 | May 19 | 🔒 Submit | UI polish (conflict card) + pitch deck + submit by 5PM |

### May 17 Task Breakdown (in priority order)
1. Agent 3 — dual output: plain-language explanation + clinical signal JSON extraction
2. Agent 1 — reconcile mode: conflict detection, three verdicts (agree / escalate / uncertain)
3. Conflict card UI — visually distinct, shown before care navigation output
4. Agent 2 — care navigation: pgvector scheme search + specialist routing
5. Agent 4 — companion: proactive check-in + "Simulate 3 Days Later" button
6. End-to-end orchestration test with demo personas

---

## What VERA Is NOT — Do Not Drift

- Not a diagnostic tool
- Not a replacement for doctors
- Not a generic health app
- Not a live camera feature
- Not a real-time doctor approval network
- Not an LLM-routed system

---

## Key Architectural Decisions — Do Not Revisit

| Decision | Reason |
|---|---|
| Deterministic router | LLM routing = unpredictable, high latency, demo crash risk |
| Agent 1 owns score field | Prevents race conditions when multiple agents produce signals |
| pending_signals not direct score overwrite | Collaboration happens through Agent 1, not around it |
| Mock govt APIs via RAG | Real APIs need auth, impossible in 5 days |
| Next.js PWA not React Native | No app store, faster build |
| Drop LangChain | Raw async Python simpler to debug in hackathon conditions |