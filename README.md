<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/099c8f9e-9e2b-401e-a41b-e684f8aaab53" />

<div align="center">

<img src="./assets/cover.png" width="100%" alt="VERA Cover" />

# VERA — Vital Early Risk Advisor

**AI-powered proactive cancer risk companion built with collaborative agents.**

*Catch risk early. Act earlier.*

---

![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_+_pgvector-4169E1?style=flat-square&logo=postgresql)
![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-8B5CF6?style=flat-square&logo=google)
![MedGemma](https://img.shields.io/badge/MedGemma-27B-E91E8C?style=flat-square&logo=google)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)

**Built for AI Agent Olympics · Milan AI Week 2026**

[Live Demo](#live-demo) · [Quickstart](#running-locally) · [Architecture](#architecture) · [Agents](#multi-agent-system)

</div>

---

## The Problem

Millions of people miss early cancer warning signs due to inaccessible screening, complex medical reports, fragmented healthcare systems, and a complete absence of proactive follow-up.

By the time action is taken, it is often too late.

## Our Solution

VERA is a collaborative AI healthcare companion that identifies early cancer risk, interprets medical reports in plain language, connects patients to nearby care resources, and proactively follows up through persistent AI-driven engagement — all in one seamless experience.

---

## Why VERA Matters

VERA is designed for regions where:

- specialist access is limited and geographically dispersed
- medical literacy is low and reports go unread
- preventive care is fragmented across public and private systems
- patients disappear between screenings with no continuity of care

**The goal is simple:** catch cancer risk before it becomes a crisis.

---

## Live Demo

> A recorded walkthrough is available in `demo-recorder/output/vera-demo.mp4`

| Onboarding | Risk Dashboard |
|---|---|
| ![Onboarding](assets/onboarding.png) | ![Risk](assets/risk.png) |

| Care Navigation | AI Chat |
|---|---|
| ![Schemes](assets/schemes.png) | ![Chat](assets/chat.png) |

---

## Multi-Agent System

VERA is built on four collaborative agents with a shared memory layer. Each agent has a distinct responsibility; together they form a complete care companion.

| Agent | Role | Responsibility |
|---|---|---|
| **Risk Profiler** | Analyst | Scores dynamic cancer risk from your health profile. Re-runs as a reconciler when new clinical signals arrive from uploaded reports. |
| **Care Navigator** | Connector | Finds nearby specialists and government schemes (Ayushman Bharat, NHS, NHIA) matched to your risk level and location. |
| **Records Explainer** | Interpreter | Reads uploaded lab reports and MRI scans. Explains findings in plain language and extracts clinical signals that feed back into the Risk Profiler. |
| **Companion** | Guardian | Maintains proactive check-ins, medication reminders, follow-up appointment reminders, and a persistent longitudinal health timeline. |

---

## AI Workflow

```
User answers health intake questions
         ↓
Risk Profiler calculates baseline risk score
         ↓
User uploads lab reports or MRI scans
         ↓
Records Explainer extracts clinical signals
         ↓
Risk Profiler re-runs as reconciler with new signals
         ↓
Care Navigator recommends specialists & schemes
         ↓
Companion maintains follow-up continuity
```

---

## Architecture

```
┌──────────────────────────────────────────┐
│            Frontend (Next.js 16)         │
│         Tailwind CSS · App Router        │
└─────────────────┬────────────────────────┘
                  │ HTTP / REST
┌─────────────────▼────────────────────────┐
│         API Gateway (FastAPI)            │
│         Python AsyncIO · /docs           │
└──────┬──────────────────────┬────────────┘
       │                      │
┌──────▼──────┐        ┌──────▼──────────────────────┐
│  AI Agents  │        │  Services                    │
│             │        │  ├── Session Store           │
│  ├── Risk   │        │  ├── Gemini Client           │
│  │  Profiler│        │  └── Database (PostgreSQL)   │
│  ├── Care   │        └──────────────────────────────┘
│  │  Navigator         
│  ├── Records│        ┌──────────────────────────────┐
│  │  Explainer│       │  PostgreSQL 16 + pgvector    │
│  └── Companion│      │  Schema · Government Seeds   │
└──────────────┘       └──────────────────────────────┘
                                    │
              ┌─────────────────────▼──────────────────┐
              │        AI Models                        │
              │  Gemini 2.0 Flash · MedGemma 27B        │
              └─────────────────────────────────────────┘
```

---

## Key Features

- Dynamic cancer risk scoring powered by MedGemma 27B
- Multi-agent orchestration with shared clinical signal pipeline
- AI medical report and MRI scan interpretation in plain language
- Government healthcare scheme discovery (Ayushman Bharat, NHS, NHIA)
- Location-aware specialist recommendations
- Persistent care reminders and proactive check-ins
- Longitudinal patient health timeline
- Secure session-based workflows with no permanent report storage in demo mode

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 16, Tailwind CSS, App Router |
| Backend | FastAPI, Python AsyncIO |
| AI Models | Gemini 2.0 Flash, MedGemma 27B |
| Vector Search | pgvector |
| Database | PostgreSQL 16 |
| Infrastructure | Docker Compose, Vultr |
| Demo Automation | Playwright |

---

## Running Locally

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js 18+](https://nodejs.org/) for the frontend
- A Google Gemini API key — get one free at [aistudio.google.com](https://aistudio.google.com)

### 1. Clone the repository

```bash
git clone https://github.com/sathyapriyakarthikeyan27/vera-hackathon.git
cd vera-hackathon
```

### 2. Configure environment variables

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

- `db` — PostgreSQL 16 with pgvector; runs schema migrations and seeds government scheme data automatically
- `backend` — FastAPI on port 8000

Verify the backend is healthy:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"VERA API","version":"0.1.0"}
```

Interactive API docs: **http://localhost:8000/docs**

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

### 5. Try the full flow

1. Click **Talk to VERA** on the landing page
2. Complete the signup form (Name, Age, Gender, Location, Language)
3. Answer the 4–5 health questions in the chat
4. Review your risk profile at `/risk`
5. Explore care navigation at `/schemes`

---

## Demo Recorder

The `demo-recorder/` folder contains a Playwright script that records a full video walkthrough of the application.

```bash
cd demo-recorder
npm install
npx playwright install chromium
node record.js
```

Output is saved to `demo-recorder/output/` as `.webm`. To convert to MP4 (requires [ffmpeg](https://ffmpeg.org/)):

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

## Privacy & Security

VERA is designed with healthcare data sensitivity at its core.

- Secure session-based workflows with no cross-user data leakage
- No permanent storage of uploaded reports in demo mode
- Environment-based secret management via `.env`
- Vectorized semantic retrieval without exposing raw patient data
- Medical signals processed in-memory within each session lifecycle

---

## Roadmap

- Voice-based multilingual support (Hindi, Tamil, Telugu, Kannada)
- Wearable device integration for continuous risk monitoring
- Real-time hospital bed and appointment availability
- AI-assisted appointment booking and confirmation
- Federated medical learning across anonymised patient cohorts
- Native mobile application (iOS and Android)

---

## Built For

**AI Agent Olympics — Milan AI Week 2026**
Track: Collaborative Agent Swarms
Submission deadline: May 19, 5PM

Powered by:

- [Google Gemini](https://deepmind.google/technologies/gemini/) — primary AI backbone
- [MedGemma](https://deepmind.google/technologies/gemini/medgemma/) — clinical risk scoring
- [Vultr](https://www.vultr.com/) — cloud infrastructure

---

<div align="center">

Built with empathy, AI, and proactive healthcare in mind.

</div>
