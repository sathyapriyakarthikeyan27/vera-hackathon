# ARCHITECTURE — VERA

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Chat UI  │  │ Risk     │  │ Scheme   │  │Education │   │
│  │(Companion)│  │ Timeline │  │ Cards    │  │ Video    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼──────────────┼─────────┘
        │             │             │              │
        └─────────────┴─────────────┴──────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Orchestration API    │
                    │   (FastAPI / Python)   │
                    │   Deployed on Vultr    │
                    └───┬───┬───┬───┬───────┘
                        │   │   │   │
          ┌─────────────┘   │   │   └─────────────┐
          │                 │   │                  │
    ┌─────▼──────┐   ┌──────▼─┐ │  ┌─────────────▼──┐
    │   Risk     │   │Scheme  │ │  │  Education      │
    │  Profiler  │   │Navig.  │ │  │  Agent          │
    │  Agent     │   │Agent   │ │  │                 │
    └─────┬──────┘   └──────┬─┘ │  └─────────────┬──┘
          │                 │   │                 │
          └─────────────────┘   │   ┌─────────────┘
                                │   │
                    ┌───────────▼───▼──────────┐
                    │   Companion Agent         │
                    │   (session memory)        │
                    └──────────────────────────┘

External Services:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ Google Gemini│  │  MedGemma    │  │ Vultr (infra) │
  │ 2.0 Flash    │  │ (via Google) │  │               │
  └──────────────┘  └──────────────┘  └──────────────┘
```

## Component Breakdown

### Frontend — Next.js

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **State**: React Context or Zustand (lightweight)
- **Key Pages**:
  - `/` — Landing + VERA intro
  - `/chat` — Main conversation interface (all 4 agents surface here)
  - `/risk` — Risk profile result + visual timeline
  - `/schemes` — Matched government schemes + clinic map
  - `/learn` — Education video + text summary
  - `/companion` — Follow-up plan + family message

### Backend — FastAPI (Python)

- **Framework**: FastAPI
- **Deployment**: Vultr (single instance, Docker container)
- **Role**: Orchestrates the 4 agents, manages session state, routes to AI APIs
- **Endpoints**:
  - `POST /session` — create new session
  - `POST /risk/question` — stream next Risk Profiler question
  - `POST /risk/score` — compute and return risk score
  - `POST /schemes/match` — return matched schemes + clinics
  - `POST /education/generate` — return video URL + text summary
  - `POST /companion/followup` — return follow-up plan + message draft
  - `GET /session/{id}` — retrieve session (Companion memory)

### Session Store

- **Demo**: SQLite (embedded, zero-config)
- **Production**: Redis
- Stores: session_id, user profile, risk score, language, agent state
- TTL: 30 days for demo, configurable

## AI Model Routing

### Gemini (Google AI Studio)

Used for:
- Risk Profiler: conversational question flow, reasoning over answers
- Scheme Navigator: scheme description summarization, eligibility matching
- Education Agent: personalized script generation (multilingual)
- Companion Agent: multilingual follow-up text, family message drafting

Model: `gemini-2.0-flash` (speed priority) or `gemini-2.0-pro` (quality priority)

### MedGemma

Used for:
- Risk Profiler: medical risk assessment over patient profile
- Model: `medgemma-4b-it` (primary); rule-based fallback if unavailable
- Accessed via Google AI Studio — same API key as Gemini

### Model Routing Logic

```
User answers complete
        ↓
MedGemma (medical risk scoring — structured JSON output)
        ↓ (concurrent)
Gemini 2.0 Flash (warm plain-language summary)
        ↓
Risk profile returned to frontend
```

## Data Flow — Full Session

```
1. User opens VERA
   → Frontend creates session (POST /session)
   → Companion Agent loads prior session if exists

2. Risk Profiler phase
   → Frontend streams 8 questions from Gemini
   → User answers stored in session
   → On completion: Featherless computes risk score
   → Gemini formats output + generates timeline data
   → Frontend renders risk card + visual timeline

3. Scheme Navigator phase
   → Backend receives location + risk profile
   → Scheme matching against seed data (+ Gemini for descriptions)
   → Returns schemes + clinic list sorted by distance
   → Frontend renders scheme cards + clinic tiles

4. Education phase
   → Backend receives risk type + language
   → Gemini generates personalized script
   → Video segment selected/assembled from pre-rendered library
   → Returns video URL + text summary
   → Frontend plays video

5. Companion phase
   → All session context passed to Companion Agent
   → Gemini generates follow-up plan + family message
   → Session saved with timestamp
   → On next visit: session loaded, user greeted by name
```

## Deployment — Vultr

```
Vultr Cloud Instance
  ├── Docker container: FastAPI backend
  ├── Nginx reverse proxy (HTTPS)
  ├── SQLite data volume (or Redis container)
  └── Static file serving for pre-rendered video segments

Frontend: Vercel (Next.js — free tier, fastest deploy)
  OR
Frontend: Vultr Object Storage + CDN (if Vultr award requires full Vultr stack)
```

## Environment Variables

```
GEMINI_API_KEY=          # covers both Gemini 2.0 Flash and MedGemma
SESSION_SECRET=
DATABASE_URL=sqlite:///./vera.db
CORS_ORIGINS=https://vera-demo.vercel.app
VULTR_REGION=blr1        # Bangalore for India latency
```

## Demo Stability Plan

- All agent responses have hardcoded fallbacks
- If MedGemma is unavailable → use deterministic rule-based fallback scoring
- If video pipeline fails → show text summary only
- If geolocation denied → default to Delhi NCR for demo
- Session seed: pre-load demo user "Priya" so Companion memory works instantly
