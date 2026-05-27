# VERA — Vital Early Risk Advisor

A proactive cancer risk companion powered by 4 collaborative AI agents.

---

## What VERA Does

VERA catches cancer risk before it becomes a crisis. It generates personalised adaptive questions, scores your risk, finds free government schemes and specialists near you, reads uploaded lab reports in plain language, and stays with you through proactive check-ins and report Q&A.

**Four agents, one mission:**

- **Agent 1 — Risk Profiler**: Generates adaptive AI questions based on your gender, age, BMI, and location. Scores cancer risk and produces a plain-language explanation. Also runs as reconciler when uploaded records change the picture.
- **Agent 2 — Care Navigator**: Finds government schemes (Ayushman Bharat, NHS, NHIA) and the nearest specialist matched to your risk and location using pgvector similarity search.
- **Agent 3 — Records Explainer**: Reads uploaded lab reports, MRI scans, and pathology reports using Gemini 2.5 Pro. Explains findings in plain language and extracts clinical signals that feed back into Agent 1.
- **Agent 4 — Companion**: Powers real-time report Q&A chat, proactive check-ins, and follow-up plans. Uses the actual session context — not static responses.

**Conflict detection**: Agent 3 surfaces clinical evidence that contradicts Agent 1's profile-based score. Agent 1 reconciles both sources, detects the conflict, and updates the risk level — surfacing the change to the user as a conflict card.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router, PWA), Tailwind CSS v4 |
| Backend | FastAPI (Python, async) |
| Database | PostgreSQL 16 + pgvector |
| AI | Gemini 2.5 Flash (Agents 1, 2, 4) + Gemini 2.5 Pro (Agent 3) |
| Embeddings | `models/embedding-001` (768-dimensional, pgvector RAG) |
| Reverse proxy | Caddy (port 80) |
| Infrastructure | Docker Compose |

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

### 2. Create environment files

`.env` (root):
```env
GEMINI_API_KEY=your_gemini_api_key_here
POSTGRES_PASSWORD=vera_dev
SESSION_SECRET=any-random-string
CORS_ORIGINS=http://localhost
```

`backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql://vera:vera_dev@db:5432/vera
SESSION_SECRET=any-random-string
CORS_ORIGINS=http://localhost
```

### 3. Start

```bash
docker compose up -d --build
```

### 4. Open

**http://localhost** — not `localhost:3000`

```bash
curl http://localhost/api/health
# {"status":"ok","service":"VERA API","version":"0.1.0"}
```
