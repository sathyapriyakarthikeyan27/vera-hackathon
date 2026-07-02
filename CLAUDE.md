# VERA — Claude Code Context File
**Vital Early Risk Advisor**
Last updated: June 26, 2026

---

## What You Are Building

A proactive cancer risk companion with 4 specialised agents that collaborate through shared state. Not a symptom checker. Not a generic health app. A focused system that catches cancer risk before it becomes a crisis.

**VERA is for everyone — any age, any gender, any location.** Do not frame VERA as a women's health app. Cancer risk is universal.

---

## VERA's Voice — Apply Everywhere

All user-facing content must sound like VERA speaking directly to the person. Not a system. Not a product. A caring, knowledgeable companion.

- **First person:** "I", "me", "I'll", "I've found", "I'm here"
- **Second person:** Address as "you" — never "the user", never "patients"
- **Tone:** Warm, unhurried, never clinical or alarming
- **Style:** Short sentences. Plain language. No jargon.
- **Confidence without preaching:** VERA informs, never lectures
- **No "truth" framing:** Do not use phrases like "the truth about your health". VERA is caring, not confrontational.
- **No em dashes anywhere in user-facing content.** Use commas, short sentences, or line breaks instead.

This applies to: landing page, signup, chat, risk output, conflict card, companion messages, education content, scheme navigator output, error messages, loading states.

---

## Status: Production

VERA is a live production application. It began as a Milan AI Week 2026 project, but that phase is
over. Build for real users following industry best practices. Do not frame decisions around
"judges", "demo reliability", or a submission deadline. Features should be complete, correct, and
maintainable.

- **AI:** Google Gemini (2.5 Flash + Pro)
- **Deployment:** Vultr (Docker Compose)

---

## The Four Agents

| Agent | Name | Role |
|---|---|---|
| Agent 1 | Risk Profiler | Scores cancer risk from user profile. Also runs as reconciler when new clinical signals arrive. |
| Agent 2 | Care Navigator | Finds nearest specialists, government schemes, screening camps based on risk score. |
| Agent 3 | Records Explainer | Reads uploaded lab reports and MRIs. Explains in plain language AND extracts structured clinical signals for Agent 1. |
| Agent 4 | Companion | Proactive check-ins, medication reminders, follow-up appointment reminders. |

---

## Authentication

### Current state: Production auth — email + password and Google OAuth

Full authentication is **implemented** (Phase 0 of the reminders program). Magic link / OTP was
evaluated and dropped in favour of production-grade accounts.

**Mechanics:**
- **Email + password:** Argon2id hashing, email verification, password reset. Min 8 chars.
- **Google OAuth:** Authorization Code flow (`/api/auth/google/login` → `/api/auth/google/callback`).
  Disabled gracefully (503) if `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are unset.
- **Tokens:** stateless access JWT (~15 min) + opaque, DB-backed, rotating refresh token
  (~30 days), both in **httpOnly, SameSite=Lax cookies** (`vera_access`, `vera_refresh`).
  `COOKIE_SECURE=true` in production. Refresh, email-verify, and reset tokens are stored **hashed**
  (SHA-256) in `auth_tokens`, single-use, expiring.

**Backend:** `services/security.py` (hashing + JWT), `services/auth_store.py` (users, oauth accounts,
tokens), `routers/auth.py` (endpoints + `get_current_user` dependency), `services/email.py` (verify /
reset sender — dev-logs the link if no provider). Tables: `users` (+ `password_hash`, `email_verified`),
`oauth_accounts`, `auth_tokens`, and `sessions.user_id` now populated.

**Frontend:** `lib/auth.tsx` (`AuthProvider`, `useAuth`, `useRequireAuth`). Pages: `/login`,
`/register`, `/forgot-password`, `/reset-password`, `/verify-email`. Flow pages (`/signup` profile,
`/assessment`, `/risk`, `/care`, `/records`, `/chat`, `/companion`) are guarded by `useRequireAuth`.
The anonymous `vera_session_id` is bound to the account via `/api/auth/link-session` after profile
submission. `vera_profile_complete` / `vera_assessment_complete` remain as local progress flags only.

**Roadmap:** phone/email verification for the notification channels, per-provider consent, session
revocation UI.

---

## Onboarding Flow

### Signup — Minimal Friction (No auth required)
Collect only these fields. No language selector (English only for now).

```
Name | Date of Birth | Gender | Location | Height (cm) | Weight (kg)
```

**Implementation details:**
- **DOB input:** `<input type="date">`. Frontend computes `age_group` enum from DOB using `computeAgeGroup()`. Backend receives `age_group`, not raw DOB.
- **Gender options:** Female / Male / Non-binary / Prefer not to say. Frontend maps "non-binary" and "prefer_not_to_say" → `"other"` before sending to backend (backend accepts `female|male|other`).
- **Location:** `CityCombobox` searchable dropdown. ~200 global cities. Filters by `startsWith` on city name.
- **Height + Weight:** In a "Biometrics" card (`bg-secondary-container`). Both optional. Used to compute BMI.
- **BMI:** Computed in the backend signup endpoint: `round(weight_kg / (height_cm / 100) ** 2, 1)`. Stored in `risk_state.answers.bmi`. Passed to Agent 1 for AI question generation.
- **Language:** Hardcoded to `"en"` in signup submission. No user-facing selector.
- **After submit:** Sets `vera_session_id` + `vera_profile_complete` in localStorage. Redirects to `/assessment`.

**Age group enum:** `under_25 | 25_34 | 35_44 | 45_54 | 55_plus`

### Assessment — Adaptive AI-Generated Questions (`/assessment`)
After signup, Agent 1 generates questions dynamically via Gemini. UI is card-based, not chat-style.

**AI question generation:**
- Gemini generates each question based on: `gender`, `age_group`, `bmi`, `location`, previous answers
- Returns structured JSON: `{ id, question, type, key, options, optional, why_we_ask }`
- `MAX_ASSESSMENT_QUESTIONS = 6` — shown as "Step 1 of 6" progress

**Question types:**
- `choice` — auto-advances on click, no separate submit button
- `text` — textarea + Continue button + optional Skip

**Key tracking:** `question_keys` dict in `risk_state` maps `"q1"` → actual answer key (e.g. `"family_history"`). Frontend passes `question.key` when calling `answerRisk`. Backend stores answer under correct key.

**Always ask (context-dependent):**
- Family history of cancer
- Existing medical conditions
- Smoking / alcohol / tobacco use
- Cervical/mammogram/prostate/colonoscopy screening history (filtered by age + gender)
- Optional symptoms field: "Is there anything health-related that has been worrying you?"

**Progress indicator:** "Step X of 6" in header badge + progress bar. Critical for users 50+.

**Tone:** Warm, human. One question at a time. Never all at once.

**On complete:** Sets `vera_assessment_complete = "1"` in localStorage. Redirects to `/risk`.

---

## Internationalisation (i18n)

### Current state: English Only (multi-language on the roadmap)

i18n (next-intl) is **not yet active**. All UI strings are currently hardcoded in English directly in components.

**What this means in practice:**
- Do NOT use `t()` from next-intl in new components
- Do NOT read from `messages/*.json` files
- Hardcode all strings in English in TSX
- Language is set to `"en"` in signup and session — backend still accepts the field but it's always `"en"`

**Roadmap:** next-intl is already installed and `messages/en.json` partially exists. Priority languages: English, Hindi, Tamil, Arabic. Re-enabling requires wrapping components with `useTranslations` and moving strings to `messages/*.json`.

---

## Accessibility — WCAG 2.1 AA

Every screen must meet WCAG 2.1 Level AA. Accessibility is a core product requirement, not an afterthought.

**Non-negotiables:**
- All interactive elements have `aria-label` or associated `<label>`
- Focus indicators are visible (do not remove outline on focus)
- Minimum touch target size: 44x44px for all buttons
- Minimum body font size: 16px (not 12px or 14px)
- Colour contrast ratio: 4.5:1 for normal text, 3:1 for large text
- Images and icons have meaningful `alt` attributes
- Form fields have associated labels (not just placeholders)
- Skip navigation link at the top of every page
- All pages keyboard-navigable in a logical order
- No information conveyed by colour alone (risk levels must use text + colour)

**For users over 50:**
- All text minimum 16px
- Buttons clearly labelled with words, not just icons
- Error messages appear next to the field, not in a toast that disappears
- Never rely on hover for critical information

---

## Core Features

### Feature 1 — Risk Advisor (Agent 1)

**Purpose:** Proactively assess cancer risk from profile data and optional symptoms. Not a symptom checker — upstream of symptoms.

**Inputs:** User profile (age, gender, family history, conditions, medications, symptoms if provided)

**Output:** Risk level — `low` | `medium` | `high`

**Behaviour by risk level:**

| Risk Level | Action |
|---|---|
| Low | Education content + periodic check-in scheduled via Agent 4 |
| Medium | Screening recommendation + Agent 2 activated |
| High | Urgent specialist referral + Agent 2 activated immediately |
| High + symptoms present | Urgent referral flagged as time-sensitive. Show emergency contact information. |

**Risk Explainability (important):**
Every risk output must include a plain-language explanation of WHY VERA assigned that score. Example: "I rated your risk as medium because of your family history of colorectal cancer and the fact that you have not had a colonoscopy in over 5 years." Users need this, and it keeps VERA's reasoning transparent and auditable.

**Specialist routing logic:**

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
5. Downloadable care plan PDF (name, risk level, recommended specialist, scheme, next steps)

**Government schemes (mocked via RAG in pgvector — not real APIs):**

| Country | Scheme |
|---|---|
| India | Ayushman Bharat (PM-JAY) |
| Egypt | NHIA (National Health Insurance Authority) |
| UK | NHS — free cancer screening programmes |

**Filters applied:** User location, cost preference, risk urgency

**Note:** All hospital and scheme data is synthetic JSON stored in pgvector. Do not attempt to call real government APIs. This is a deliberate architectural decision.

---

### Feature 3 — Health Records Explainer (Agent 3)

**Purpose:** Read uploaded medical documents and explain them in plain language. Also extract structured clinical signals for Agent 1.

**Supported file types:** PDF, JPG, PNG (lab reports, MRI scans, prescriptions, pathology reports)

**Model:** Gemini 2.5 Pro for records and medical image analysis. MedGemma was evaluated as an alternative (purpose-built for clinical content) but is not currently used. Gemini Vision is NOT used.

**Behaviour:**
- Explains findings in the user's preferred language — no medical jargon
- Flags anything that needs urgent attention explicitly
- Answers follow-up questions about the report in the same session
- Produces dual output: user explanation + clinical signals JSON (see Agent 3 section below)

**Privacy:** Files processed in memory only. Deleted immediately after response via `try/finally`. Never stored. Never logged. This deletion guarantee is a hard privacy requirement.

**What Agent 3 must NOT do:**
- Diagnose
- Tell the user they have cancer
- Contradict a doctor's report
- Store or cache the file after processing

---

### Feature 4 — Companion Agent (Agent 4)

**Purpose:** Proactive health companionship. VERA reaches out — users do not have to remember to come back.

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
- Reminds 3 days before and day of appointment

**Educational content:**
- What to expect at a first oncology appointment
- How to prepare for a colonoscopy
- Personalised to the user's risk type — not generic

**Persistent memory:**
- Every check-in conversation stored in pgvector, linked to user_id
- Agent 4 builds a living health timeline per user
- Used to personalise future messages and surface patterns over time

**Proactive check-ins:** Check-ins fire on a real schedule (FastAPI BackgroundTasks). There is no
"Simulate 3 Days Later" button in the production UI. A hidden internal endpoint (`/companion/checkin`)
may remain for testing only — it must not be exposed in the user-facing UI.

---

## Tech Stack

### Frontend
- Next.js 16 (PWA — mobile-first, no app store needed)
- Tailwind CSS v4 (CSS-first config via `@theme` in `globals.css` — no `tailwind.config.js`)
- Care & Clarity design system: custom tokens, typography utilities, `soft-elevation`
- English only for now (next-intl not yet active)

### Backend
- FastAPI (Python) — async
- Deterministic rule-based router — NOT LLM-based routing
- FastAPI BackgroundTasks for scheduling

### Database
- PostgreSQL — users, sessions, appointments, reminders, auth tokens
- pgvector — vector embeddings, conversation memory, mock hospital and scheme data (RAG)

### AI Models

| Model | Purpose |
|---|---|
| Gemini 2.5 Flash | Conversations, routing, multilingual content generation |
| Gemini 2.5 Pro | Medical risk reasoning, records understanding, medical image analysis |

Note: Gemini Vision is NOT used. MedGemma is NOT used. Preferred for prod as it handles all medical document and image analysis. This is a deliberate decision — MedGemma is purpose-built for clinical content and produces more reliable structured output than a general-purpose vision model.

### Infrastructure
- Vultr — deployment
- Vultr Object Storage — temporary health record storage, deleted immediately after response
- Redis — cache-aside layer for user-agnostic LLM results (Agent 2 schemes/clinics, embeddings). See Caching section.
- Docker — containerised

### Explicitly Dropped (do not reintroduce)
- LangChain
- Real government APIs (scheme and hospital data is synthetic, served via RAG in pgvector)
- Gemini TTS (not in scope yet)
- MedGemma (Gemini 2.5 Pro handles records and image analysis)

### Reversed decisions
- **Celery reintroduced** for the reminders/notifications program: Celery Beat schedules time-based
  reminders and workers deliver them (in-app / email / SMS / WhatsApp) with retries. Redis is now
  **dual-purpose** — cache-aside for LLM results **and** the Celery broker/result backend (separate
  logical DBs). This supersedes the earlier "drop Celery / Redis is cache-only" stance. Scheduled
  delivery is Phase 2 of the reminders plan (see `docs/reminders-plan.md`); until then no scheduler runs.

### Reminder channels (all implemented — see `docs/reminders-plan.md`)
- In-app (bell/banner), email, SMS, and WhatsApp are all built behind `services/channels.py`.
  Each is dev-safe: without provider credentials the message is logged (recipient masked) instead of
  sent. Set `EMAIL_PROVIDER`/`EMAIL_API_KEY` (Resend/SendGrid) and `TWILIO_*` to go live. Delivery is
  gated on opt-in + consent + verified contact (email verified / phone OTP).

### Not yet implemented (on the roadmap, not dropped)
- next-intl / multi-language (currently English only)

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

**Important:** The router is deterministic by design. Do not replace it with an LLM-based planner. Deterministic = reliable, low-latency, predictable in production.

---

## Caching (LLM result cache)

VERA caches at two levels:

1. **Per-session output cache (PostgreSQL).** Each agent's output (`schemes_output`,
   `companion_output`, etc.) is stored on the session row and returned on repeat requests within
   that session. Cleared when a reconciliation changes the picture (e.g. `companion_output` after a
   conflict).

2. **Cross-session LLM cache (Redis, cache-aside).** User-agnostic Gemini results are shared across
   sessions and users so the same work is not regenerated for every person.

**What is cached cross-session (Agent 2 / Care Navigator only):**
- Government scheme generation — key: `schemes:{location}:{risk}:{cancer_types}:{gender}:{age_group}`
- Nearby hospital / clinic lookup — key: `clinics:{location}:{cancer_types}:{specialist}:{gender}`
- Scheme-search embeddings — key: the query text

**Rules:**
- Opt-in only, via `gemini.generate_cached()` / `gemini.embed_text_cached()`. Plain `generate()` /
  `embed_text()` are uncached. **Never cache personalized output** (companion chat, risk reasoning,
  records explanations) or anything containing PII.
- **Fail-open:** any Redis error or outage is treated as a cache miss; the request falls through to a
  live Gemini call. The cache can never break a request. The app also runs cache-less if `REDIS_URL`
  is unset.
- TTLs: scheme/clinic results 7 days; embeddings 30 days. Redis handles eviction (`allkeys-lru`).
- Implementation: `services/cache.py` (Redis client), cached wrappers in `services/gemini.py`,
  wired in `agents/scheme_navigator/agent.py`. Tests in `tests/test_llm_cache.py`.

---

## Collaborative Architecture — The Core Feature

This is what makes VERA a collaborative agent system, not just a pipeline.

### The Shared Risk Assessment Object

Every agent reads from and writes to this shared object in PostgreSQL. Agent 1 is the only agent that writes the final `score`. All other agents write to `pending_signals`.

```python
risk_assessment = {
    "score": "low" | "medium" | "high",  # Agent 1 owns this field
    "confidence": 0.0 to 1.0,
    "source": "profile_only" | "profile+records",
    "reasoning": str,                    # Plain-language explanation of score
    "pending_signals": [],               # Agent 3 writes here, never Agent 1
    "reconciled": bool,                  # False = reconciliation needed
    "conflict": None | {
        "original_score": str,
        "new_score": str,
        "reason": str,
        "shown_to_user": bool
    }
}
```

**Rule:** No agent overwrites `score` directly except Agent 1. This prevents race conditions.

---

### Collaboration Mechanic 1 — Conflict Detection

**The scenario:** Agent 1 scores a user as MEDIUM risk from their profile. The user later uploads a lab report. Agent 3 reads it and finds high-severity clinical signals. Agent 1 reconciles, conflict is detected, score changes to HIGH. The user sees the conflict surfaced explicitly.

**Why this matters:** The agents are not just passing data — they are checking each other's conclusions. A finding from one agent changes the output of another. That is genuine collaboration.

---

### Agent 3 — Dual Output

Agent 3 produces TWO outputs for every uploaded document:

**Output 1 — User-facing explanation**
Plain language summary in the user's preferred language. Flags anything urgent. No em dashes.

**Output 2 — Clinical signals for Agent 1**

```
After generating the user explanation, extract clinical signals as JSON:
{
  "anomalies": ["list of findings"],
  "severity": "high" | "medium" | "low",
  "confidence": 0.0 to 1.0,
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

### Agent 1 — Reconciliation Mode

Agent 1 has two modes:

```python
def get_agent1_mode(user_profile):
    ra = user_profile.risk_assessment
    if not ra["reconciled"] and len(ra["pending_signals"]) > 0:
        return "reconcile"
    return "initial_profile"
```

**Agent 1 reconciler outputs one of three verdicts:**

```python
# Verdict A — Agreement (signals confirm original score)
{
    "final_score": "medium",
    "conflict": False,
    "reasoning": "Lab findings are consistent with your existing risk profile."
}

# Verdict B — Escalation (signals contradict original score)
{
    "final_score": "high",
    "conflict": True,
    "reasoning": "Your lab report shows findings that indicate higher risk than your initial profile suggested."
}

# Verdict C — Uncertainty (signals are mixed)
{
    "final_score": "medium",
    "conflict": True,
    "uncertain": True,
    "reasoning": "Your report contains mixed signals. I recommend a follow-up with a specialist to get a clearer picture."
}
```

After reconciliation:
- Write `final_score` to `risk_assessment.score`
- Write conflict object to `risk_assessment.conflict`
- Set `risk_assessment.reconciled = True`
- Clear `risk_assessment.pending_signals`
- If `conflict = True`, surface conflict message to user before routing to Agent 2

**Verdict C matters.** VERA admitting uncertainty is more credible and safer for users than always being confident. Do not skip it.

---

### What the User Sees on Conflict

When `conflict = True`, show this before the care navigation output:

> "I've updated your risk assessment. Your profile initially pointed to [ORIGINAL SCORE] risk. But your [document type] has changed that picture. I now consider your risk to be [NEW SCORE]. Here is why: [REASON]. Here is what I recommend next."

This moment is a key part of the experience. Make it visually distinct in the UI. A different card, a different colour, not just a text update. No em dashes in the copy.

---

## Full Collaboration Flow (End-to-End Sequence)

```
1. User lands on homepage, clicks "Start Assessment"
         |
2. Signup (/signup): Name, DOB, Gender, Height, Weight, Location
   Frontend computes age_group from DOB, BMI from height+weight
   Backend stores all in risk_state.answers, including bmi
         |
3. Agent 1 (initial mode) at /assessment
   AI-generated adaptive questions (6 questions, one at a time)
   Gemini generates each question based on gender/age_group/bmi/location/prior answers
   Scores risk: MEDIUM
   Writes to risk_assessment: score=medium, source=profile_only
   Writes reasoning: plain-language explanation of score
         |
4. Agent 2 activates
   Shows medium-risk recommendation (screening, not urgent referral)
   Shows Ayushman Bharat / NHIA / NHS scheme
         |
5. User uploads colonoscopy report
         |
6. Agent 3 (dual output)
   Explains report to user in plain language
   Extracts: {anomalies: ["abnormal polyp"], severity: "high", urgency_flag: true}
   Writes to pending_signals
   Sets reconciled = False
         |
7. Router sees pending_signals, routes to Agent 1 (reconcile mode)
         |
8. Agent 1 (reconcile mode)
   Original: MEDIUM | New signal: HIGH
   CONFLICT DETECTED
   Writes: score=high, conflict={original: medium, new: high, reason: "..."}
         |
9. User sees conflict card:
   "I've updated your assessment from MEDIUM to HIGH based on your report."
         |
10. Agent 2 activates with HIGH risk
    Nearest Gastroenterologist
    Ayushman Bharat / NHIA / NHS scheme shown
    Downloadable care plan PDF offered
```

---

## Privacy Architecture

- Health records never stored. Processed in memory, deleted immediately after response.
- Use explicit `try/finally` block for file deletion.
- User profile encrypted at rest
- No PII in logs
- Session-based processing for all medical documents
- Session ID stored in localStorage (no auth tokens yet — see Authentication)
- In-app disclaimer: "VERA is a health awareness tool, not a medical device"
- LLM cache (Redis) only ever stores user-agnostic results (schemes, hospitals, embeddings). Never personalized content, never PII.

```python
# File is always deleted, even on exception — hard privacy requirement
async def process_health_record(file):
    temp_path = save_temporarily(file)
    try:
        result = await ai.analyze(temp_path)
        return result
    finally:
        os.remove(temp_path)  # always deleted, even on exception
```

---

## Multilingual Support

**Not yet active.** All content is currently English only. See i18n section above.

Backend session still stores `language: "en"`. Agent prompts include it in case Gemini defaults help, but no UI language switching exists.

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
| Deterministic router | LLM routing = unpredictable, higher latency, harder to test |
| Agent 1 owns score field | Prevents race conditions when multiple agents produce signals |
| pending_signals not direct score overwrite | Collaboration happens through Agent 1, not around it |
| Synthetic govt/hospital data via RAG | Real government APIs require per-country auth and partnerships; synthetic RAG data is the current approach |
| Next.js PWA not React Native | No app store, single codebase, installable on mobile |
| Drop LangChain | Raw async Python is simpler to debug and maintain |
| Redis cache-aside for LLM results | User-agnostic schemes/hospitals/embeddings reused across sessions; shared across workers, TTL-native, keeps load off Postgres |
| Production auth (email+password + Google OAuth) | Argon2 + JWT/refresh httpOnly cookies. Replaces the localStorage-only session. Magic link / OTP evaluated and dropped. Durable identity is required for scheduled reminders. |
| English only (i18n on roadmap) | Multi-language is a tracked roadmap item; UI strings are currently hardcoded English |
| MedGemma evaluated, Gemini 2.5 Pro in use | Gemini 2.5 Pro currently handles records and image analysis |
| AI-generated assessment questions | Static questions feel like a form. Gemini generates contextual questions per user. |
| BMI computed at signup, passed to Agent 1 | Height + weight collected at signup. BMI informs question relevance and risk score. |
| `/assessment` not `/chat` for risk profiling | Card-based UI shows structured progress and is clearer than a chat transcript. |
| DOB input → age_group enum | Natural input for users. Frontend computes backend enum. |
| WCAG 2.1 AA target | Accessibility is a core requirement for a health product serving all ages and abilities |
| Tailwind v4 CSS-first (no tailwind.config.js) | All tokens in `globals.css` via `@theme`. Cleaner, no config file. |
