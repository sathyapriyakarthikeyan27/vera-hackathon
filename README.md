# VERA — Vital Early Risk Advisor

A proactive cancer risk companion powered by 4 collaborative AI agents.
Built for the AI Agent Olympics, Milan AI Week 2026.

---

## What VERA Does

VERA catches cancer risk before it becomes a crisis. It asks a few honest questions, scores your risk using MedGemma, finds free government schemes and specialists near you, reads your uploaded lab reports, and stays with you through check-ins and reminders.

**Four agents, one mission:**
- **Agent 1 — Risk Profiler:** Scores cancer risk from your profile. Re-runs as reconciler when new clinical signals arrive from uploaded reports.
- **Agent 2 — Care Navigator:** Finds nearest specialists, government schemes (Ayushman Bharat, NHS, NHIA), and screening camps matched to your risk and location.
- **Agent 3 — Records Explainer:** Reads uploaded lab reports and MRI scans. Explains in plain language and extracts clinical signals that feed back into Agent 1.
- **Agent 4 — Companion:** Proactive check-ins, medication reminders, follow-up appointment reminders, and a persistent health timeline.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, Tailwind CSS |
| Backend | FastAPI (Python, async) |
| Database | PostgreSQL 16 + pgvector |
| AI | Gemini 2.0 Flash, MedGemma 27B |
| Infrastructure | Docker, Vultr |

---

## Running Locally

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js 18+](https://nodejs.org/) for the frontend
- A Google Gemini API key — get one free at [aistudio.google.com](https://aistudio.google.com)

### 1. Clone the repo

```bash
git clone https://github.com/sathyapriyakarthikeyan27/vera-hackathon.git
cd vera-hackathon
```

### 2. Set your environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
GEMINI_API_KEY=your_gemini_api_key_here
POSTGRES_PASSWORD=vera_dev
SESSION_SECRET=any-random-string-here
```

### 3. Start the backend and database

```bash
docker compose up --build -d
```

This starts two containers:
- `db` — PostgreSQL 16 with pgvector, runs the schema and seeds government scheme data automatically
- `backend` — FastAPI on port 8000

Verify it is running:
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"VERA API","version":"0.1.0"}
```

API docs are at: **http://localhost:8000/docs**

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

### 5. Try the full flow

1. Click **Talk to VERA** on the landing page
2. Fill in the signup form (Name, Age, Gender, Location, Language)
3. Answer the 4-5 health questions in the chat
4. See your risk profile at `/risk`
5. Explore care navigation at `/schemes`

---

## Running the Demo Recorder

The `demo-recorder/` folder contains a Playwright script that records a video walkthrough of the app.

```bash
cd demo-recorder
npm install
npx playwright install chromium
node record.js
```

The output `.webm` video is saved to `demo-recorder/output/`.

To convert to mp4 (requires [ffmpeg](https://ffmpeg.org/)):
```bash
ffmpeg -i output/<file>.webm -c:v libx264 output/vera-demo.mp4
```

---

## Project Structure

```
vera-hackathon/
├── backend/
│   ├── agents/          # The 4 VERA agents
│   ├── routers/         # FastAPI route handlers
│   ├── services/        # Database, Gemini, session store
│   ├── db/              # Schema SQL + seed data
│   └── main.py          # App entrypoint + lifespan
├── frontend/
│   ├── app/             # Next.js App Router pages
│   └── lib/api.ts       # Typed API client
├── demo-recorder/       # Playwright video recorder (not part of the app)
├── docker-compose.yml
└── CLAUDE.md            # Full architecture and build context
```

---

## Hackathon

**Event:** AI Agent Olympics — Milan AI Week 2026
**Track:** Collaborative Agent Swarms
**Partners:** Google Gemini (primary), Vultr (deployment)
**Submission deadline:** May 19, 5PM
