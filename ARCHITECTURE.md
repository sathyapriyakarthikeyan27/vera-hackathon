# ARCHITECTURE — VERA

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js — Vercel)                        │
│                                                                            │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────┐  │
│  │ Landing  │  │  Signup  │  │ Assessment │  │  /risk   │  │  /care  │  │
│  │   /      │  │ /signup  │  │/assessment │  │          │  │         │  │
│  └──────────┘  └──────────┘  └────────────┘  └──────────┘  └─────────┘  │
│                                                                            │
│  ┌──────────┐  ┌──────────┐                                               │
│  │ Records  │  │  Chat    │                                               │
│  │ /records │  │  /chat   │                                               │
│  └──────────┘  └──────────┘                                               │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │  Next.js rewrites /api/* → Vultr
                                   ▼
                    ┌──────────────────────────┐
                    │   Caddy (port 80)         │
                    │   Reverse proxy           │
                    │   /api/* → backend:8000   │
                    │   /* → frontend:3000      │
                    └─────────────┬────────────┘
                                  │
                    ┌─────────────▼────────────┐
                    │   FastAPI Backend          │
                    │   Deterministic Router     │
                    │   (Python, async)          │
                    └───┬───┬───┬───┬───────────┘
                        │   │   │   │
          ┌─────────────┘   │   │   └──────────────────┐
          │                 │   │                       │
   ┌──────▼──────┐  ┌───────▼─┐ │  ┌──────────────────▼──┐
   │  Agent 1    │  │ Agent 2  │ │  │    Agent 3            │
   │  Risk       │  │ Care     │ │  │    Records Explainer  │
   │  Profiler   │  │ Navigator│ │  │                       │
   │  + Reconcile│  │          │ │  └──────────────────┬───┘
   └──────┬──────┘  └───────┬──┘ │                     │
          │                 │    │  ┌──────────────────▼───┐
          └─────────────────┘    │  │    Agent 4             │
                                 └─►│    Companion           │
                                    │    (check-ins)         │
                                    └────────────────────────┘

                    ┌───────────────────────────────┐
                    │   Shared State (PostgreSQL)    │
                    │   risk_assessment JSONB        │
                    │   session_store, appointments  │
                    │   pgvector: RAG + memory       │
                    └───────────────────────────────┘

External Services:
  ┌──────────────────┐  
  │  Gemini 2.0 Flash│   
  │  Questions, risk  │  
  │  summaries, chat  │  
  └──────────────────┘ 
```

---

## Component Breakdown

### Frontend — Next.js (Vercel)

- **Framework**: Next.js (App Router)
- **Styling**: Tailwind CSS v4 (CSS-first, no tailwind.config.js — tokens in `globals.css` via `@theme`)
- **Design system**: Care & Clarity — custom tokens, typography utilities, `soft-elevation`
- **i18n**: English only (next-intl not yet active; roadmap item)
- **Session**: localStorage — `vera_session_id`, `vera_profile_complete`, `vera_assessment_complete`
- **Key Pages**:
  - `/` — Landing page with shared Navbar + Footer
  - `/signup` — Profile collection (name, DOB, gender, location, height, weight)
  - `/assessment` — AI-generated adaptive questions (6, card UI, one at a time)
  - `/risk` — Risk result + plain-language reasoning + conflict card if reconciliation fired
  - `/care` — Government schemes + nearest specialist (Agent 2)
  - `/records` — Upload lab reports/MRIs, plain-language explanation (Agent 3) + chat CTA
  - `/chat` — Report Q&A chat with VERA (sidebar + scrollable message area)

### Shared Components

- **`Navbar`** — fixed top, active state via `usePathname()`, optional `right` prop
- **`Footer`** — centered, Care & Clarity tokens, disclaimer + copyright
- **`StartAssessmentButton`** — client component handling localStorage routing logic

### Backend — FastAPI (Vultr, Docker)

- **Framework**: FastAPI (async)
- **Role**: Deterministic router + agent orchestration + session persistence
- **Key Endpoints**:
  - `POST /signup` — create session, store profile, compute BMI
  - `POST /risk/start` — create session + return first AI-generated question
  - `POST /risk/answer` — submit answer, return next question or final score
  - `POST /risk/reconcile` — Agent 1 reconcile mode (triggered after pending_signals arrive)
  - `POST /records/upload` — Agent 3: explain document + extract clinical signals JSON
  - `POST /schemes/match` — Agent 2: matched schemes + specialists by location + risk
  - `POST /companion/chat` — Agent 4: chat message
  - `GET /session/{id}` — retrieve full session state
  - `GET /health` — health check

### Deterministic Router Logic

```python
if user.is_new:
    route_to(Agent1)               # initial profiling
elif payload.file_uploaded:
    route_to(Agent3)               # records + signal extraction
elif payload.is_scheduled_trigger:
    route_to(Agent4)               # proactive check-in
elif risk_assessment.pending_signals and not risk_assessment.reconciled:
    route_to(Agent1)               # reconcile mode
else:
    route_to(Agent2)               # care navigation
```

The router is deterministic by design. Never replace with an LLM-based planner.

---

## Database Schema

### PostgreSQL Tables

```sql
-- Sessions (active conversation state — no user accounts yet; full auth on roadmap)
session_store (
  session_id    TEXT PRIMARY KEY,
  data          JSONB,              -- full session state
  created_at    TIMESTAMPTZ,
  updated_at    TIMESTAMPTZ
)

-- Companion memory (pgvector)
checkin_memory (
  id            UUID PRIMARY KEY,
  session_id    TEXT,
  role          TEXT,              -- 'vera' | 'user'
  content       TEXT,
  embedding     vector(768),
  created_at    TIMESTAMPTZ
)

-- Government scheme data (pgvector RAG — synthetic data, no real APIs)
scheme_data (
  id            UUID PRIMARY KEY,
  scheme_name   TEXT,
  country       TEXT,
  cancer_types  TEXT[],
  content       TEXT,
  metadata      JSONB,
  embedding     vector(768)
)
```

### Shared Risk Assessment Object (JSONB in session_store)

```python
risk_assessment = {
    "score":            "low" | "medium" | "high",   # Agent 1 owns this
    "confidence":       0.0-1.0,
    "reasoning":        str,                          # plain-language explanation
    "source":           "profile_only" | "profile+records",
    "pending_signals":  [],                           # Agent 3 writes here only
    "reconciled":       bool,
    "conflict": None | {
        "original_score": str,
        "new_score":      str,
        "reason":         str,
        "shown_to_user":  bool
    }
}
```

---

## AI Model Routing

### Gemini 2.0 Flash

Used for:
- Agent 1: Adaptive question generation, plain-language risk summary
- Agent 2: Scheme description summarization, eligibility matching
- Agent 4: Check-in and chat message generation
- Embeddings: `models/embedding-001` (768-dimensional, v1beta compatible)

### Gemini 2.5 Pro — Agent 3 only

Used for:
- Reading uploaded lab reports, MRI scans, pathology reports (PDF, JPG, PNG)
- Extracting structured clinical signals JSON from medical documents
- Plain-language explanation of medical findings

**Gemini Pro handles all document types including images. Gemini Vision and MedGemma are not used.**

---

## Deployment

### Vultr (Full Stack — Primary Demo)

```
Vultr Dedicated CPU (2 vCPU / 8GB RAM)
  └── Docker Compose
        ├── db          pgvector/pgvector:pg16
        │                 schema.sql + seed.py (scheme RAG data)
        ├── backend     FastAPI on port 8000 (internal only)
        ├── frontend    Next.js standalone on port 3000 (internal only)
        └── caddy       Port 80 (HTTP, auto-HTTPS disabled for IP deployment)
                          /api/* → strips prefix → backend:8000
                          /*     → frontend:3000
```

### Vercel (Frontend — Alternative)

- Next.js deployed on Vercel (free tier, CI/CD on push to `feature/demo-ready`)
- `BACKEND_URL=http://<vultr-ip>/api` — Next.js rewrites `/api/*` → Vultr backend via Caddy
- `output: "standalone"` disabled on Vercel (conditional on `DOCKER_BUILD=1`)

---

## Environment Variables

### Root `.env` (Docker Compose)

```
GEMINI_API_KEY=          # Gemini 2.0 Flash + embeddings
POSTGRES_PASSWORD=       # PostgreSQL password
SESSION_SECRET=          # Session signing secret
DOMAIN=                  # Server IP or domain (Caddy binding)
CORS_ORIGINS=            # Allowed origins (e.g. http://<ip> or https://<domain>)
```

### `backend/.env` (inside backend container)

```
GEMINI_API_KEY=
DATABASE_URL=postgresql://vera:<POSTGRES_PASSWORD>@db:5432/vera
SESSION_SECRET=
CORS_ORIGINS=
```

### Vercel Environment Variables

```
BACKEND_URL=http://<vultr-ip>/api
```
