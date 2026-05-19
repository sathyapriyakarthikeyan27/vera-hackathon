# VERA — Vital Early Risk Advisor

A proactive cancer risk companion powered by 4 collaborative AI agents.
Built for the AI Agent Olympics, Milan AI Week 2026.

---

## What VERA Does

VERA catches cancer risk before it becomes a crisis. It generates personalised adaptive questions, scores your risk, finds free government schemes and specialists near you, reads uploaded lab reports in plain language, and stays with you through proactive check-ins and report Q&A.

**Four agents, one mission:**

- **Agent 1 — Risk Profiler**: Generates adaptive AI questions based on your gender, age, BMI, and location. Scores cancer risk and produces a plain-language explanation. Also runs as reconciler when uploaded records change the picture.
- **Agent 2 — Care Navigator**: Finds government schemes (Ayushman Bharat, NHS, NHIA) and the nearest specialist matched to your risk and location using pgvector similarity search.
- **Agent 3 — Records Explainer**: Reads uploaded lab reports, MRI scans, and pathology reports using Gemini 2.5 Pro. Explains findings in plain language and extracts clinical signals that feed back into Agent 1.
- **Agent 4 — Companion**: Powers real-time report Q&A chat, proactive check-ins, and follow-up plans. Uses the actual session context — not static responses.

**The centrepiece**: Conflict detection. Agent 3 surfaces clinical evidence that contradicts Agent 1's profile-based score. Agent 1 reconciles both sources, detects the conflict, and updates the risk level — surfacing the change to the user as a conflict card.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router, PWA), Tailwind CSS v4 |
| Backend | FastAPI (Python, async) |
| Database | PostgreSQL 16 + pgvector |
| AI | Gemini 2.5 Flash (Agents 1, 2, 4) + Gemini 2.5 Pro (Agent 3) |
| Embeddings | `models/embedding-001` (768-dimensional, pgvector RAG) |
| Reverse proxy | Caddy (port 80, auto-HTTPS disabled for IP deployment) |
| Infrastructure | Docker Compose, Vultr Dedicated CPU |

---

## Running Locally

### Prerequisites

- Docker Desktop installed and running
- A Google Gemini API key — get one at [aistudio.google.com](https://aistudio.google.com)

### 1. Clone the repo

```bash
git clone <repo-url>
cd hackathon-vera
```

### 2. Create the environment file

```env
# .env (root directory)
GEMINI_API_KEY=your_gemini_api_key_here
POSTGRES_PASSWORD=vera_dev
SESSION_SECRET=any-random-string
CORS_ORIGINS=http://localhost
```

Also create `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql://vera:vera_dev@db:5432/vera
SESSION_SECRET=any-random-string
CORS_ORIGINS=http://localhost
```

### 3. Start everything

```bash
docker compose up -d --build
```

This starts four containers:
- `db` — PostgreSQL 16 with pgvector; runs schema and seeds government scheme data
- `backend` — FastAPI on port 8000 (internal only)
- `frontend` — Next.js standalone on port 3000 (internal only)
- `caddy` — Port 80; routes `/api/*` to backend, `/*` to frontend

### 4. Open the app

**http://localhost** (port 80 through Caddy, not port 3000)

Verify backend is running:
```bash
curl http://localhost/api/health
# {"status":"ok","service":"VERA API","version":"0.1.0"}
```

API docs: **http://localhost/docs** (Swagger UI served by Caddy via `/openapi.json` route)

### 5. Try the full flow

1. Click **Start Your Assessment** on the landing page
2. Fill in the signup form (Name, DOB, Gender, Location — Height and Weight optional)
3. Answer the AI-generated adaptive questions (up to 6)
4. See your risk profile at `/risk`
5. Explore care navigation at `/care`
6. Upload a medical document at `/records` to trigger conflict detection
7. Chat about your report at `/chat`

---

## Project Structure

```
hackathon-vera/
├── backend/
│   ├── agents/
│   │   ├── risk_profiler/     # Agent 1: adaptive questions, risk scoring, reconciler
│   │   ├── care_navigator/    # Agent 2: scheme matching, specialist routing
│   │   ├── records_explainer/ # Agent 3: Gemini Pro multimodal, dual output
│   │   └── companion_agent/   # Agent 4: chat, check-ins, follow-up
│   ├── routers/               # FastAPI route handlers
│   ├── services/
│   │   ├── gemini.py          # Gemini client (Flash + Pro), retry logic, embeddings
│   │   ├── session_store.py   # PostgreSQL session persistence
│   │   └── database.py        # asyncpg pool, pgvector helpers
│   ├── db/
│   │   ├── schema.sql         # Tables: session_store, checkin_memory, scheme_data
│   │   └── seed.py            # Seeds synthetic scheme data with embeddings
│   └── main.py                # App entrypoint, lifespan, routers, session endpoints
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Landing page
│   │   ├── signup/            # Profile collection
│   │   ├── assessment/        # AI-generated adaptive questions
│   │   ├── risk/              # Risk result + conflict card
│   │   ├── care/              # Government schemes + specialist
│   │   ├── records/           # Document upload + Agent 3 output
│   │   └── chat/              # Report Q&A chat (Agent 4)
│   ├── components/
│   │   ├── Navbar.tsx
│   │   └── Footer.tsx
│   └── lib/api.ts             # Typed API client (BASE="/api", all calls through Caddy)
├── Caddyfile                  # Reverse proxy config
├── docker-compose.yml
└── CLAUDE.md                  # Full architecture, design decisions, build context
```

---

## Environment Variables

### Root `.env` (Docker Compose substitution)

```
GEMINI_API_KEY=        # Gemini 2.5 Flash + Pro + embeddings
POSTGRES_PASSWORD=     # PostgreSQL password
SESSION_SECRET=        # Session signing secret
CORS_ORIGINS=          # Allowed origins (e.g. http://localhost or http://<vultr-ip>)
```

### `backend/.env` (read by load_dotenv() inside the container)

```
GEMINI_API_KEY=
DATABASE_URL=postgresql://vera:<POSTGRES_PASSWORD>@db:5432/vera
SESSION_SECRET=
CORS_ORIGINS=
```

---

## Hackathon

**Event**: AI Agent Olympics — Milan AI Week 2026
**Track**: Collaborative Agent Swarms
**Partners**: Google Gemini (primary), Vultr (deployment)
**Submission deadline**: May 19, 5PM
**Live demo**: May 20, Milan
