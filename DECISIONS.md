# DECISIONS — VERA Decision Log

This file records significant decisions made during planning and development, and the reasoning behind them. Update this as new decisions are made.

---

## Project Name: VERA

**Decision**: Name the project VERA (Vital Early Risk Advisor)

**Alternatives considered**: ASHA, CLARA, SNEHA

**Reasoning**:
- Acronym is precise and self-explanatory: Vital Early Risk Advisor
- Globally pronounceable — works in Milan, Mumbai, Manila
- No translation needed; the name carries its own meaning
- Self-contained: no cultural context required to understand it

**Rejected alternatives**:
- ASHA: Strong resonance in India but loses meaning internationally; already used by India's national ASHA health worker program (confusion risk)
- SNEHA: Beautiful meaning in Telugu/Sanskrit but difficult for Western audiences to pronounce
- CLARA: Less distinctive, no strong thematic connection

---

## Target Audience: Everyone

**Decision**: VERA is for everyone — any age, any gender, any location. It is not a women's health app.

**Reasoning**:
- Cancer risk is universal — men, women, and non-binary individuals all face risk
- Framing as women's health excludes 50% of the audience and creates demo bias
- Judging panel is global; a universal framing scores broader
- The 4-agent architecture works for any cancer type, any demographic

**Impact on content**: All copy uses "you" — never "women", never "patients". VERA speaks directly to the person.

---

## Track Selection: Collaborative Agent Swarms

**Decision**: Enter the Collaborative Agent Swarms track

**Alternatives considered**: General AI, Healthcare AI

**Reasoning**:
- VERA's 4-agent architecture is genuinely collaborative — each agent has a distinct role
- The conflict detection mechanic (Agent 3 findings changing Agent 1 score) is direct proof of agent collaboration
- The track rewards multi-agent design, which is VERA's core differentiator
- Gives a clearer judging lens to optimize presentation against

---

## 4-Agent Architecture

**Decision**: Build 4 distinct agents with separate responsibilities

**Alternatives considered**: Single agent handling all tasks, 2-agent split (risk + action)

**Reasoning**:
- Collaborative Systems track rewards visible agent collaboration
- Each barrier (risk awareness, cost, fear, follow-up) needs a different capability set
- Separation allows different AI models to be used for each agent's specialty
- Demo is more compelling when each agent's contribution is visible

**Trade-off accepted**: More complexity, more integration points — mitigated by clear interfaces between agents and the shared `risk_assessment` object.

---

## Shared State: Agent 1 Owns `score`

**Decision**: Only Agent 1 may write to `risk_assessment.score`. All other agents write to `pending_signals`.

**Reasoning**:
- Prevents race conditions when multiple agents produce signals simultaneously
- Collaboration happens through Agent 1, not around it
- Makes the audit trail clear: every score change is attributable to a reconciliation run
- `pending_signals` creates a clear handoff contract between Agent 3 and Agent 1

---

## Deterministic Router

**Decision**: The orchestration router is deterministic (code-based conditions), not LLM-based.

**Alternatives considered**: LLM planner deciding which agent to invoke

**Reasoning**:
- LLM routing is unpredictable, adds latency, and introduces demo crash risk
- The routing logic is simple enough to express in 5 lines of Python
- Demo-safe: the router will never hallucinate a wrong agent during a live presentation
- Judges can read the router and understand the collaboration flow immediately

---

## Model Split: Gemini 2.0 Flash + Gemini 2.5 Pro

**Decision**: Gemini 2.0 Flash for all agents except Agent 3. Gemini 2.5 Pro for Agent 3 (document analysis and clinical signal extraction).

**Alternatives considered**: MedGemma 27B via Featherless, Gemini only with one model

**Reasoning**:
- Gemini 2.0 Flash is fast and cost-effective for question generation, risk scoring, scheme matching, and companion chat
- Gemini 2.5 Pro provides stronger reasoning for structured extraction from complex medical documents — compensates for the absence of clinical fine-tuning
- One API key covers both models — no additional credentials or services
- Rule-based fallback ensures demo stability if any model call fails

---

## MedGemma Removed for Demo — Gemini Only

**Original decision**: MedGemma 27B (via Featherless API) for medical risk assessment and document analysis.

**Revised decision (hackathon)**: Gemini models only. No MedGemma, no Featherless dependency.

| Agent | Model |
|---|---|
| Agent 1, 2, 4 | Gemini 2.0 Flash (`gemini-2.0-flash`) |
| Agent 3 (document analysis) | Gemini 2.5 Pro (`gemini-2.5-pro`) |

**Reasoning**:
- MedGemma requires Vertex AI access not available on a standard Gemini API key
- Featherless free tier has cold-start delays (up to 90s) — unacceptable for a live demo
- Gemini 2.5 Pro is capable of reading and reasoning over medical documents with explicit prompting
- Agent 3 prompt enhanced with explicit JSON field definitions to compensate for the absence of clinical fine-tuning
- One API key, two models — simpler ops, no second service to manage

**Post-hackathon**: MedGemma via Vertex AI is the right long-term choice for clinical accuracy.

---

## Gemini Vision Removed — Gemini Pro Handles All Documents

**Decision**: Remove Gemini Vision from the model list. Gemini 2.5 Pro handles all document types including images (PDF, JPG, PNG) for Agent 3.

**Reasoning**:
- Gemini 2.5 Pro is a capable multimodal model that can read and reason over medical documents with explicit prompting
- Using a separate vision model adds complexity with no benefit
- Fewer models = fewer API calls, lower latency, simpler error handling

---

## Authentication: Dropped for Demo — localStorage Session

**Original decision**: Email OTP, 6-digit code, JWT in httpOnly cookie.

**Revised decision (hackathon)**: Authentication dropped entirely. Session persistence via localStorage.

**Three localStorage keys**:
- `vera_session_id` — backend session UUID, set after signup
- `vera_profile_complete` — set after signup form submission
- `vera_assessment_complete` — set after risk assessment completes

**Reasoning**:
- Auth adds demo risk: email delivery can fail, OTP can expire mid-demo, cookie handling across domains adds complexity
- localStorage session persists for the duration of the demo (2-3 hours) — sufficient for judges
- No user accounts, no auth tokens — backend session store holds all state by session UUID

**Post-hackathon**: Add `users` + `auth_tokens` tables, link `session.user_id`. The architecture already supports it.

---

## i18n: Dropped for Demo — English Only

**Original decision**: next-intl with static JSON files for en, hi, ta, ar.

**Revised decision (hackathon)**: i18n dropped. All UI strings hardcoded in English directly in TSX components.

**Reasoning**:
- next-intl wrapper in `next.config.ts` caused Docker build failures
- Demo judges are English speakers — no multilanguage needed for Milan presentation
- Removes an entire class of locale routing and message file errors during demo

**Post-hackathon**: next-intl is installed. Re-enable by wrapping components with `useTranslations()` and moving strings to `messages/*.json`. Priority languages: English, Hindi, Tamil, Arabic.

---

## Accessibility: WCAG 2.1 AA

**Decision**: Target WCAG 2.1 AA compliance throughout the application.

**Reasoning**:
- VERA's users include older adults and people with lower digital literacy — accessibility is not optional
- Healthcare applications are frequently audited for accessibility compliance
- 44px touch targets, 16px minimum font, 4.5:1 contrast ratio, full keyboard navigation
- Judges notice when an AI healthcare demo is unusable for the populations it claims to serve
- Reduced-motion support respects users with vestibular disorders

---

## No Em Dashes in User-Facing Content

**Decision**: Em dashes (—) are banned from all user-facing copy.

**Reasoning**:
- Em dashes read as AI-generated in 2026; they break the warm, human tone VERA requires
- Users with cognitive disabilities or low literacy find em dashes harder to parse
- Sentence structure should carry the rhythm — commas, periods, and line breaks do the job
- Applies to: landing page, signup, chat messages, risk output, conflict card, companion messages

---

## No Passwords, No Jargon, No Em Dashes — VERA's Design Principles

**Decision**: Three non-negotiable content and design constraints apply to the entire app.

1. No passwords (auth by OTP)
2. No jargon (plain language throughout)
3. No em dashes (human tone, not AI tone)

These are listed together because they all serve the same user: someone who is anxious about their health, possibly over 50, possibly not tech-savvy, who needs to trust VERA immediately.

---

## Demo Personas

**Primary — Arjun**
- 45-54 male, smoker, family history of colorectal cancer, Mumbai
- Initial score: MEDIUM (profile only)
- Uploads colonoscopy report with abnormal polyp
- Conflict fires: score escalates to HIGH
- Agent 2: Gastroenterologist + Ayushman Bharat

**Secondary — Priya**
- 38-year-old, family history of breast cancer, no prior screening
- Score: HIGH from profile alone (no conflict scenario)
- Agent 2: Gynaecologic Oncologist

**Tertiary — Post-diagnosis user**
- On chemotherapy
- Agent 4 demo: medication reminders + "Simulate 3 Days Later" button

Personas are pre-seeded in the database. Demo button bypasses auth and loads Arjun's session directly.

---

## Backend Language: Python (FastAPI)

**Decision**: Use Python with FastAPI for the backend agent orchestration layer

**Alternatives considered**: Node.js (Express), Go

**Reasoning**:
- Python is the dominant language in AI/ML tooling — all AI SDKs have first-class Python support
- FastAPI is async-first, clean for concurrent agent calls
- Faster to iterate with AI pair-programming in Python for AI patterns

---

## Frontend: Next.js 16 (PWA)

**Decision**: Use Next.js 16 with App Router as a PWA (no app store required)

**Alternatives considered**: Plain React, Vue.js, React Native

**Reasoning**:
- App Router supports streaming responses (important for agent conversation flow)
- PWA means judges can use it on any device during the demo without installing anything
- Fast deployment on Vercel
- No app store review delay during a hackathon

---

## Database: PostgreSQL + pgvector (No Redis, No SQLite)

**Decision**: Use PostgreSQL 16 with pgvector for all storage: relational data, vector embeddings, and RAG.

**Alternatives considered**: SQLite for demo, Redis for sessions, separate vector DB (Pinecone, Weaviate)

**Reasoning**:
- pgvector enables vector similarity search in the same database as relational data — one fewer infrastructure component
- PostgreSQL handles sessions, user profiles, appointments, medications, and RAG in one place
- SQLite cannot support concurrent connections from multiple Docker containers
- Redis adds operational complexity (Celery + Redis) — FastAPI BackgroundTasks covers the scheduling needs

---

## Scheduling: FastAPI BackgroundTasks (No Celery, No Redis)

**Decision**: Use FastAPI's built-in BackgroundTasks for medication and appointment reminders.

**Alternatives considered**: Celery + Redis, APScheduler, cron jobs

**Reasoning**:
- Celery + Redis requires two additional services — too much infrastructure for a hackathon
- BackgroundTasks is built into FastAPI, zero additional dependencies
- Sufficient for demo: reminders fire in the same process, no cross-service coordination needed
- "Simulate 3 Days Later" demo button manually triggers the reminder flow — no real scheduling needed for the demo

---

## No Real Government APIs — Mock via RAG

**Decision**: All government scheme data (Ayushman Bharat, NHIA, NHS) is synthetic JSON stored in pgvector. No real government APIs are called.

**Reasoning**:
- Real government APIs require auth, registration, and approval — impossible in 5 days
- Synthetic data is sufficient to demonstrate the matching logic
- pgvector similarity search makes the RAG demo compelling and technically interesting
- Post-hackathon: real API integrations are additive — the matching architecture stays

---

## No LangChain

**Decision**: Build agent orchestration in raw Python + asyncio. No LangChain.

**Alternatives considered**: LangChain, LlamaIndex, AutoGen

**Reasoning**:
- LangChain adds abstraction layers that are hard to debug during a live hackathon
- The routing logic is simple enough to write directly in Python
- Raw async Python is faster, more predictable, and easier to demo-fallback
- Removes an entire class of "LangChain version mismatch" bugs

---

## Privacy: Files Deleted Immediately After Processing

**Decision**: Health record files are never stored. Processed in memory, deleted immediately after response via `try/finally`.

**Reasoning**:
- Medical documents contain highly sensitive personal data
- No regulatory justification to retain uploaded files
- `try/finally` guarantees deletion even if processing fails
- Judges will ask about privacy — showing this code pattern is the answer

```python
async def process_health_record(file):
    temp_path = save_temporarily(file)
    try:
        result = await medgemma.analyze(temp_path)
        return result
    finally:
        os.remove(temp_path)  # always deleted, even on exception
```

---

## Scope Cuts — Do Not Reintroduce

| Cut | Reason |
|---|---|
| No authentication (demo) | Demo risk; localStorage session sufficient for judges |
| No i18n (demo) | next-intl caused build failures; English-only for Milan |
| No live appointment booking | Hospital APIs in India are fragmented and unreliable |
| No Gemini TTS | Stretch goal only; adds complexity, not core to judging criteria |
| No MedGemma / Featherless (demo) | Vertex AI access unavailable; cold-start latency unacceptable |
| No Gemini Vision | Gemini Pro handles all document types including images |
| No LangChain | Raw async Python simpler and more debuggable |
| No Celery + Redis | FastAPI BackgroundTasks covers all scheduling needs |
| No live camera | Privacy risk, out of scope, not needed for demo |
| No real government APIs | Auth/approval impossible in 5 days — RAG mock is sufficient |
| Embedding model: embedding-001 | text-embedding-004 not available on v1beta API |
| Caddy auto-HTTPS disabled | Let's Encrypt does not issue certs for IP addresses |

---

## What VERA Is Not — Scope Boundaries

These are design choices, not limitations:

1. Not a diagnostic tool — avoids regulatory risk, focuses on awareness
2. Not a doctor replacement — VERA is the bridge, not the destination
3. Not India-only — global architecture from day one, India-first in demo data
4. Not a generic chatbot — every output is structured, personalized, and actionable
5. Not a live camera app — privacy and scope
6. Not an LLM-routed system — deterministic router is the right choice for reliability

These boundaries make VERA more trustworthy, not less capable.
