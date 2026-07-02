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
- LLM routing is unpredictable, adds latency, and is harder to test
- The routing logic is simple enough to express in 5 lines of Python
- Reliable: the router will never hallucinate a wrong agent in production
- The router is easy to read and reason about — the collaboration flow is explicit

---

## Model Split: Gemini 2.0 Flash + Gemini 2.5 Pro

**Decision**: Gemini 2.0 Flash for all agents except Agent 3. Gemini 2.5 Pro for Agent 3 (document analysis and clinical signal extraction).

**Alternatives considered**: MedGemma 27B via Featherless, Gemini only with one model

**Reasoning**:
- Gemini 2.0 Flash is fast and cost-effective for question generation, risk scoring, scheme matching, and companion chat
- Gemini 2.5 Pro provides stronger reasoning for structured extraction from complex medical documents — compensates for the absence of clinical fine-tuning
- One API key covers both models — no additional credentials or services
- Rule-based fallback ensures stability if any model call fails

---

## MedGemma Not Used — Gemini Only

**Earlier consideration**: MedGemma 27B (via Featherless API) for medical risk assessment and document analysis.

**Current decision**: Gemini models only. No MedGemma, no Featherless dependency.

| Agent | Model |
|---|---|
| Agent 1, 2, 4 | Gemini 2.0 Flash (`gemini-2.0-flash`) |
| Agent 3 (document analysis) | Gemini 2.5 Pro (`gemini-2.5-pro`) |

**Reasoning**:
- MedGemma requires Vertex AI access not available on a standard Gemini API key
- Featherless free tier has cold-start delays (up to 90s) — unacceptable for a responsive product
- Gemini 2.5 Pro is capable of reading and reasoning over medical documents with explicit prompting
- Agent 3 prompt enhanced with explicit JSON field definitions to compensate for the absence of clinical fine-tuning
- One API key, two models — simpler ops, no second service to manage

**Roadmap**: MedGemma via Vertex AI is the right long-term choice for clinical accuracy.

---

## Gemini Vision Removed — Gemini Pro Handles All Documents

**Decision**: Remove Gemini Vision from the model list. Gemini 2.5 Pro handles all document types including images (PDF, JPG, PNG) for Agent 3.

**Reasoning**:
- Gemini 2.5 Pro is a capable multimodal model that can read and reason over medical documents with explicit prompting
- Using a separate vision model adds complexity with no benefit
- Fewer models = fewer API calls, lower latency, simpler error handling

---

## Authentication: localStorage Session (full auth on the roadmap)

**Planned end state**: Email OTP, 6-digit code, JWT in httpOnly cookie.

**Current decision**: Full authentication not yet implemented. Session persistence via localStorage.

**Three localStorage keys**:
- `vera_session_id` — backend session UUID, set after signup
- `vera_profile_complete` — set after signup form submission
- `vera_assessment_complete` — set after risk assessment completes

**Reasoning**:
- localStorage session persistence let us ship the core experience first; full auth is additive
- Session persists for 2-3 hours by session UUID — backend session store holds all state
- No user accounts or auth tokens yet — this is the current state, not the end state

**Roadmap**: Add `users` + `auth_tokens` tables, link `session.user_id`. The architecture already supports it.

---

## i18n: English Only (multi-language on the roadmap)

**Planned end state**: next-intl with static JSON files for en, hi, ta, ar.

**Current decision**: i18n not yet active. All UI strings hardcoded in English directly in TSX components.

**Reasoning**:
- next-intl wrapper in `next.config.ts` caused Docker build failures that need resolving first
- English-first let us ship the core experience; multi-language is additive
- Avoids an entire class of locale routing and message file errors until i18n is properly set up

**Roadmap**: next-intl is installed. Re-enable by wrapping components with `useTranslations()` and moving strings to `messages/*.json`. Priority languages: English, Hindi, Tamil, Arabic.

---

## Accessibility: WCAG 2.1 AA

**Decision**: Target WCAG 2.1 AA compliance throughout the application.

**Reasoning**:
- VERA's users include older adults and people with lower digital literacy — accessibility is not optional
- Healthcare applications are frequently audited for accessibility compliance
- 44px touch targets, 16px minimum font, 4.5:1 contrast ratio, full keyboard navigation
- An AI healthcare product is a failure if it is unusable for the populations it claims to serve
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

## Example Personas (test scenarios)

These personas are used as QA and regression scenarios for the agent flows.

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
- Exercises Agent 4: medication reminders and scheduled proactive check-ins

These personas can be pre-seeded for testing. Any test-only shortcut that loads a persona session directly must stay behind an internal/test path — never exposed in the production UI.

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
- PWA means users can install it on any device without an app store
- Fast deployment
- No app store review delay for updates

---

## Database: PostgreSQL + pgvector (primary store)

**Decision**: Use PostgreSQL 16 with pgvector for all durable storage: relational data, vector embeddings, and RAG. Redis is used only as a cache (see "LLM Result Cache" below), never as the primary store.

**Alternatives considered**: SQLite, Redis as primary store, separate vector DB (Pinecone, Weaviate)

**Reasoning**:
- pgvector enables vector similarity search in the same database as relational data — one fewer infrastructure component
- PostgreSQL handles sessions, user profiles, appointments, medications, and RAG in one place
- SQLite cannot support concurrent connections from multiple Docker containers
- Redis is not the primary store — it is a disposable cache layer; all durable state lives in Postgres

---

## Scheduling: FastAPI BackgroundTasks (No Celery broker)

**Decision**: Use FastAPI's built-in BackgroundTasks for medication and appointment reminders. No Celery or external task-queue broker.

**Alternatives considered**: Celery + Redis broker, APScheduler, cron jobs

**Reasoning**:
- A Celery broker is more infrastructure than the current scheduling needs require
- BackgroundTasks is built into FastAPI, zero additional dependencies
- Reminders fire in the same process; no cross-service coordination needed at current scale
- Note: Redis IS in the stack, but only as a cache layer — never as a Celery/task-queue broker
- If scheduling needs grow (multi-worker, durable retries), revisit a dedicated queue

---

## LLM Result Cache — Redis Cache-Aside

**Decision**: Cache user-agnostic Gemini results in Redis (cache-aside) so the same work is not regenerated for every user across sessions.

**Alternatives considered**: PostgreSQL-as-cache table, in-process TTL cache, no cross-session cache

**Reasoning**:
- Agent 2's government schemes, nearby hospitals, and scheme-search embeddings depend only on coarse, user-agnostic inputs (location, risk level, cancer type, specialist, gender) — they are identical across users and ideal to share
- Redis is the standard cache-aside layer: native TTL eviction, sub-millisecond reads shared across all API workers, and it keeps cache load off the primary Postgres
- Self-hosted Redis is free (a container in `docker-compose`); a managed instance (e.g. Vultr Managed Redis/Valkey) is optional via a `rediss://` `REDIS_URL`
- **Opt-in only** via `gemini.generate_cached()` / `embed_text_cached()`. Personalized output (companion chat, risk reasoning, records explanations) and anything with PII is never cached
- **Fail-open**: any Redis error or outage degrades to a live Gemini call; the app also runs cache-less if `REDIS_URL` is unset
- TTLs: scheme/clinic results 7 days, embeddings 30 days; eviction policy `allkeys-lru`

**Note**: This does not contradict "no Celery + Redis." That decision was about task-queue brokers. Redis as a cache is a separate, additive concern.

**Implementation**: `services/cache.py`, cached wrappers in `services/gemini.py`, wired in `agents/scheme_navigator/agent.py`. Tests in `tests/test_llm_cache.py`.

---

## No Real Government APIs — Mock via RAG

**Decision**: All government scheme data (Ayushman Bharat, NHIA, NHS) is synthetic JSON stored in pgvector. No real government APIs are called.

**Reasoning**:
- Real government APIs require auth, registration, and per-country partnerships
- Synthetic data exercises the matching logic end to end today
- pgvector similarity search keeps the RAG matching fast and self-contained
- Roadmap: real API integrations are additive — the matching architecture stays

---

## No LangChain

**Decision**: Build agent orchestration in raw Python + asyncio. No LangChain.

**Alternatives considered**: LangChain, LlamaIndex, AutoGen

**Reasoning**:
- LangChain adds abstraction layers that are hard to debug and maintain
- The routing logic is simple enough to write directly in Python
- Raw async Python is faster, more predictable, and easier to add fallbacks to
- Removes an entire class of "LangChain version mismatch" bugs

---

## Privacy: Files Deleted Immediately After Processing

**Decision**: Health record files are never stored. Processed in memory, deleted immediately after response via `try/finally`.

**Reasoning**:
- Medical documents contain highly sensitive personal data
- No regulatory justification to retain uploaded files
- `try/finally` guarantees deletion even if processing fails
- This pattern is the auditable answer to any privacy question about uploaded records

```python
async def process_health_record(file):
    temp_path = save_temporarily(file)
    try:
        result = await gemini.analyze(temp_path)
        return result
    finally:
        os.remove(temp_path)  # always deleted, even on exception
```

---

## Scope Cuts — Do Not Reintroduce

| Item | Status / Reason |
|---|---|
| Full authentication | Not yet implemented; localStorage session is current state (roadmap) |
| i18n / multi-language | Not yet active; English-only (roadmap) |
| Live appointment booking | Hospital booking APIs are fragmented and unreliable |
| Gemini TTS | Not in scope yet; adds complexity |
| MedGemma / Featherless | Gemini 2.5 Pro currently handles records and image analysis |
| Gemini Vision | Gemini Pro handles all document types including images |
| LangChain | Raw async Python simpler and more debuggable |
| Celery / task-queue broker | FastAPI BackgroundTasks covers scheduling. Redis is used only as a cache |
| Live camera | Privacy risk, out of scope |
| Real government APIs | Synthetic RAG data; real APIs need per-country partnerships |
| Embedding model: embedding-001 | text-embedding-004 not available on v1beta API |
| Caddy auto-HTTPS disabled | Let's Encrypt does not issue certs for IP addresses |

---

## What VERA Is Not — Scope Boundaries

These are design choices, not limitations:

1. Not a diagnostic tool — avoids regulatory risk, focuses on awareness
2. Not a doctor replacement — VERA is the bridge, not the destination
3. Not India-only — global architecture from day one, India-first in seed data
4. Not a generic chatbot — every output is structured, personalized, and actionable
5. Not a live camera app — privacy and scope
6. Not an LLM-routed system — deterministic router is the right choice for reliability

These boundaries make VERA more trustworthy, not less capable.

---

## Production Authentication (2026-07-01)

**Decision**: Implement production-grade auth — email + password (Argon2id) **and** Google OAuth —
replacing the localStorage-only session. Access = short-lived JWT; refresh = opaque, DB-backed,
rotating; both in httpOnly SameSite=Lax cookies. Email verification + password reset via single-use
hashed tokens.

**Alternatives considered**: Magic link / OTP (the previous roadmap plan); server-side session cookies.

**Reasoning**:
- The reminders program needs **durable user identity** — reminders fire days later, long after a
  2-3 hour anonymous session would expire. Accounts are the prerequisite.
- Email+password + Google covers the common cases with no third-party lock-in; Google lowers signup
  friction.
- Magic link / OTP dropped: more moving parts (deliverability, code entry UX) for weaker identity
  than a real account with a password.

**Impact**: `users`/`oauth_accounts`/`auth_tokens` tables active; `sessions.user_id` populated; flow
pages guarded by `useRequireAuth`; anonymous session bound to the account after profile submit.

---

## Reintroduce Celery + Redis broker for reminders (2026-07-01)

**Decision**: Reverse the earlier "drop Celery / Redis is cache-only" decisions. Use **Celery Beat**
to schedule time-based reminders and **Celery workers** to deliver them (in-app / email / SMS /
WhatsApp) with retry/backoff. **Redis becomes dual-purpose**: cache-aside for LLM results **and**
the Celery broker/result backend, on separate logical DBs.

**Alternatives considered**: FastAPI BackgroundTasks (non-durable, dies on restart, no cron); a custom
asyncio DB-poller (works, but reinvents scheduling/retries/monitoring).

**Reasoning**:
- Production-grade scheduled, retried, multi-channel delivery is exactly Celery Beat + workers'
  wheelhouse; Redis is already in the stack as broker.
- The DB-poller was the no-Celery fallback; since Celery is now approved, it is the more robust choice.

**Status**: Decision recorded now; implementation is Phase 2 of `docs/reminders-plan.md`. No scheduler
runs until then. Supersedes the "Celery / task-queue broker" row in Rejected Alternatives above.
