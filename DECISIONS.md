# DECISIONS — VERA Decision Log

This file records significant decisions made during planning and development, and the reasoning behind them. Update this as new decisions are made.

---

## Project Name: VERA

**Decision**: Name the project VERA (Vital Early Risk Advisor)

**Alternatives considered**: ASHA, CLARA, SNEHA

**Reasoning**:
- "Vera" means Truth in Latin — the mission is giving women truth about their health
- Acronym is precise and self-explanatory: Vital Early Risk Advisor
- Globally pronounceable — works in Milan, Mumbai, Manila
- No translation needed; the name carries its own meaning
- Self-contained: no cultural context required to understand it

**Rejected alternatives**:
- ASHA: Strong resonance in India but loses meaning internationally; already used by India's national ASHA health worker program (confusion risk)
- SNEHA: Beautiful meaning in Telugu/Sanskrit but difficult for Western audiences to pronounce
- CLARA: Less distinctive, no strong thematic connection

---

## Track Selection: Collaborative Systems

**Decision**: Enter the Collaborative Systems track

**Alternatives considered**: General AI, Healthcare AI

**Reasoning**:
- VERA's 4-agent architecture is genuinely collaborative — each agent has a distinct role
- The track rewards multi-agent design, which is VERA's core differentiator
- Collaborative Systems track aligns directly with the technical architecture already planned
- Gives us a clearer judging lens to optimize presentation against

---

## 4-Agent Architecture

**Decision**: Build 4 distinct agents with separate responsibilities

**Alternatives considered**: Single agent handling all tasks, 2-agent split (risk + action)

**Reasoning**:
- Collaborative Systems track rewards visible agent collaboration
- Each barrier (risk awareness, cost, fear, follow-up) needs a different capability set
- Separation allows different AI models to be used for each agent's specialty
- Demo is more compelling when each agent's contribution is visible
- Easier to build in parallel across team members

**Trade-off accepted**: More complexity, more integration points — mitigated by clear interfaces between agents.

---

## Model Split: Gemini + MedGemma

**Decision**: Use Gemini for conversation/language tasks and MedGemma for medical risk assessment

**Alternatives considered**: Gemini only, GPT-4 + Gemini, third-party medical APIs

**Reasoning**:
- Gemini is best-in-class for multilingual, conversational, and generative tasks
- MedGemma (medgemma-4b-it) is Google's purpose-built medical AI model trained on clinical literature — produces structured risk assessments that a general-purpose model cannot reliably replicate
- Both models are accessed through the same Google AI Studio API key — simpler ops, one less credential to manage
- MedGemma returns structured JSON (risk level, cancer types, screening gap, clinical reasoning) enabling deterministic downstream logic
- Fallback to rule-based scoring ensures demo stability if MedGemma is unavailable

---

## No Live Camera Feature

**Decision**: Education Agent uses animated video only — no live camera access

**Alternatives considered**: Allow user to photograph a lump for AI analysis

**Reasoning**:
- Privacy and safety: accessing a user's camera for medical purposes introduces serious risk
- Out of scope for v1: requires clinical validation, regulatory consideration
- Unnecessary for the demo: animated explainers serve the educational purpose fully
- Avoids any perception that VERA is doing live diagnosis
- Reduces technical complexity significantly

---

## Demo Persona: "Priya"

**Decision**: Use a consistent fictional persona named Priya for the entire demo

**Alternatives considered**: Generic "User", live demo with real user, multiple personas

**Reasoning**:
- A named persona makes the story human and emotionally resonant
- "Priya" is recognizable across India (Hindi, Tamil, Telugu names all have Priya variants) and internationally
- Consistent persona allows pre-loading session data for Companion Agent memory demo
- Avoids exposing real personal health data on a public demo stage
- 38-year-old with family history of breast cancer and 5-year screening gap represents the high-impact target user

---

## Backend Language: Python (FastAPI)

**Decision**: Use Python with FastAPI for the backend agent orchestration layer

**Alternatives considered**: Node.js (Express), Go

**Reasoning**:
- Python is the dominant language in AI/ML tooling — all AI SDKs have first-class Python support
- FastAPI is async-first, matching Featherless AI's async-first architecture
- Team's primary language for AI work is Python
- Faster to iterate with Claude Code assistance in Python for AI patterns
- Node.js considered but Python AI ecosystem advantage outweighs familiarity

---

## Frontend: Next.js

**Decision**: Use Next.js for the frontend

**Alternatives considered**: Plain React, Vue.js, Svelte

**Reasoning**:
- Team has 5 years full-stack experience; Next.js is a known quantity
- App Router supports streaming responses well (important for agent conversation flow)
- Fast deployment on Vercel as frontend host
- SSR option available for initial page load performance
- No learning curve cost during a 7-day hackathon

---

## Demo Stability: Hardcoded Fallbacks

**Decision**: All agent responses have hardcoded fallback data for demo stability

**Alternatives considered**: Live-only, graceful error handling only

**Reasoning**:
- A 7-minute live demo on stage cannot afford API failures
- Fallback data ensures the demo completes even if Gemini or Featherless is slow
- Judges care about the demo flow, not whether every response was live-generated
- Fallbacks are pre-populated with "Priya" persona data for seamless experience
- Post-hackathon: fallbacks removed or reduced to genuine error states

---

## Language Priority: English, Hindi, Tamil

**Decision**: Support English, Hindi, and Tamil for multilingual output

**Alternatives considered**: English only, all 22 scheduled Indian languages, all global languages

**Reasoning**:
- English: global accessibility, demo audience in Milan
- Hindi: 600M speakers, largest Indian language, demo relevance
- Tamil: second South Indian language chosen for diversity; team has Tamil context
- Three languages demonstrates multilingual capability convincingly without scope creep
- Gemini handles translation — adding more languages post-hackathon is a configuration change, not a rebuild

---

## Deployment Region: Vultr Bangalore (blr1)

**Decision**: Deploy backend on Vultr Bangalore region

**Alternatives considered**: Vultr New York, Vultr Singapore

**Reasoning**:
- India is the primary target market — Bangalore reduces latency for Indian users
- Aligns with the demo narrative (Priya is in Delhi — Indian infrastructure makes the story coherent)
- Bangalore Vultr region is mature and reliable
- Vultr partner award requires backend on Vultr infrastructure — blr1 satisfies this

---

## Scope Cut: No Real-Time Appointment Booking

**Decision**: Show clinic information but do not enable live appointment booking

**Alternatives considered**: Integrate with hospital booking APIs, show external links only

**Reasoning**:
- Hospital booking APIs in India are fragmented and unreliable
- Integration risk too high for 7-day hackathon
- "Call to schedule" or "Walk-in available" is honest and actionable
- Avoids demo failure if a booking API is down
- Post-hackathon: partnership with a booking aggregator is a natural next step

---

## Scope Cut: No Actual Video Generation

**Decision**: Use pre-rendered video segments + Gemini-generated narration text; no live video generation

**Alternatives considered**: Runway ML video generation, HeyGen avatar video

**Reasoning**:
- Live video generation is slow (30s–3min per video) — too slow for demo
- Quality is unpredictable and not appropriate for medical education content
- Pre-rendered animated segments can be high quality and culturally appropriate
- Gemini provides personalized intro text overlaid on the segment
- Full generative video is a compelling post-hackathon roadmap item

---

## What VERA Is Not (Scope Boundaries)

**Decision**: Explicitly define what VERA does not do

These are not limitations — they are design choices:
1. Not a diagnostic tool — avoids regulatory risk, focuses on awareness
2. Not a doctor replacement — positions VERA as the bridge, not the destination
3. Not India-only — global architecture from day one, India-first in data
4. Not a generic chatbot — every output is structured, personalized, and actionable
5. No live camera — privacy and scope

These boundaries make VERA more trustworthy, not less capable.
