# HACKATHON — AI Agent Olympics at Milan AI Week 2026

## Event Details

| Field | Value |
|-------|-------|
| Event | AI Agent Olympics |
| Conference | Milan AI Week 2026 |
| Platform | lablab.ai |
| Track | Collaborative Agent Swarms |
| Build Phase | May 13 to 19, 2026 |
| Submission Deadline | May 19, 2026 at 5:00 PM |
| Live Demo | May 20, 2026 — Milan, Italy |

---

## Our Track: Collaborative Agent Swarms

The Collaborative Agent Swarms track rewards:
- Multiple agents that work together meaningfully
- Clear division of responsibilities between agents
- Emergent capability from collaboration (the whole is greater than the sum of its parts)
- Real-world impact of the multi-agent system

VERA's 4-agent architecture is purpose-built for this track. The conflict detection mechanic — where Agent 3 findings change Agent 1's score — is the concrete proof of genuine agent collaboration.

---

## Technical Partners

### Google Gemini (Primary)

- **Models used**: `gemini-2.5-flash` (Agents 1, 2, 4), `gemini-2.5-pro` (Agent 3)
- **Award criteria**: Must demonstrate meaningful Gemini integration beyond basic API calls
- **Our usage**:
  - Agent 1: AI-generated adaptive assessment questions, risk scoring, reconciliation
  - Agent 2: Scheme matching, eligibility summarization, specialist routing
  - Agent 3: Multimodal document analysis (PDF, JPG, PNG), clinical signal extraction
  - Agent 4: Chat responses, follow-up plans, proactive check-in messages
  - Embeddings: `models/embedding-001` for pgvector RAG (scheme matching)

### Vultr (Deployment)

- **Why required**: Backend deployment infrastructure for live demo
- **Award criteria**: Backend must actually run on Vultr
- **Our usage**: Full-stack Docker deployment on Vultr Dedicated CPU (2 vCPU / 8GB)
  - Docker Compose: `db` (pgvector), `backend` (FastAPI), `frontend` (Next.js), `caddy` (reverse proxy)
  - Caddy handles port 80, routes `/api/*` to backend, `/*` to frontend

---

## Judging Criteria and How VERA Scores

| Criterion | Weight | VERA's Angle |
|-----------|--------|-------------|
| Model integration effectiveness | High | Gemini 2.5 Flash + Pro used distinctly; Flash for reasoning/conversation, Pro for multimodal document analysis |
| Presentation clarity | High | 7-minute scripted demo with Arjun persona; conflict card is the centrepiece |
| Practical business impact | High | Cancer risk awareness for everyone, real government schemes, real cost barriers addressed |
| Uniqueness and creativity | High | Conflict detection mechanic — two agents checking each other's conclusions, score changes in real time |

---

## Submission Requirements Checklist

### Technical

- [ ] Google Gemini integrated and demonstrable (gemini-2.5-flash + gemini-2.5-pro)
- [ ] Backend deployed and accessible on Vultr
- [ ] GEMINI_API_KEY active and not rate-limited
- [ ] Full end-to-end demo flow works (tested 3x)
- [ ] Conflict card fires after colonoscopy upload
- [ ] GitHub repository public and linked

### Content

- [ ] Project name: VERA — Vital Early Risk Advisor
- [ ] Track: Collaborative Agent Swarms
- [ ] Team members listed
- [ ] Demo video (3 minutes max) uploaded
- [ ] Project description written (see below)
- [ ] Partner logos credited

### lablab.ai Submission Form Fields

- **Project name**: VERA — Vital Early Risk Advisor
- **Tagline**: The AI companion that catches cancer risk before it becomes a crisis
- **Track**: Collaborative Agent Swarms
- **Partners used**: Google Gemini, Vultr
- **GitHub URL**: [to be added]
- **Demo URL**: `http://<vultr-ip>`
- **Demo video**: [upload pre-recorded walkthrough]

---

## Project Description (for submission)

> VERA (Vital Early Risk Advisor) is a proactive cancer risk companion powered by 4 collaborative AI agents. In a 7-minute interaction, VERA:
>
> - **Agent 1 — Risk Profiler**: Generates adaptive assessment questions using Gemini 2.5 Flash, personalised to the user's gender, age, BMI, location, and prior answers. Scores cancer risk and produces a plain-language explanation of why.
>
> - **Agent 2 — Care Navigator**: Matches the user to free government health programs (Ayushman Bharat, NHS, NHIA) and finds the nearest specialist using pgvector similarity search over synthetic scheme data.
>
> - **Agent 3 — Records Explainer**: Reads uploaded lab reports and MRI scans using Gemini 2.5 Pro (multimodal). Produces two outputs: a plain-language explanation for the user, and structured clinical signals written to the shared risk assessment object for Agent 1.
>
> - **Agent 4 — Companion**: Powers proactive check-ins, report Q&A chat, and follow-up plans. Uses the full session context to answer questions about the user's actual uploaded document.
>
> The defining feature is conflict detection: Agent 3 surfaces clinical evidence that contradicts Agent 1's profile-based score. Agent 1 reconciles both sources, detects the conflict, and updates the risk level — surfacing the change to the user with a plain-language explanation. The agents are not a pipeline; they check each other's conclusions.
>
> Built on Google Gemini 2.5 Flash and Pro. Deployed on Vultr with Docker Compose.

---

## Build Timeline

| Day | Date | Status | Focus |
|-----|------|--------|-------|
| Day 1 | May 13 | Done | Repo setup, frontend skeleton, backend scaffold |
| Day 2 | May 14 | Done | Risk assessment schema, Agent 1 initial profiling |
| Day 3 | May 15 | Done | Signup flow, DB bootstrap, Agent 1 reconcile mode |
| Day 4 | May 16 | Done | Agent 3 dual output, conflict detection, Agent 2, Agent 4, Care & Clarity UI |
| Day 5 | May 17 | Done | Assessment page, AI-generated questions, localStorage session, BMI, CityCombobox |
| Day 6 | May 18 | Done | Full demo run, Vultr deployment, MOCK=false on all pages, docs updated |
| Day 7 | May 19 | Today | Bug fixes, model update (gemini-2.5-flash), chat fix, submit by 5PM |
| Demo Day | May 20 | Tomorrow | Live presentation — Milan |

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Gemini rate limits during demo | Low | Separate demo API key with higher quota; retry logic built in |
| Vultr deployment fails | Low | Keep full Docker Compose local fallback; deploy confirmed before demo |
| Conflict card does not fire | Low | Test Arjun persona end-to-end 3x before demo; fallback: describe mechanic verbally |
| Demo overruns 7 minutes | Medium | Practice 5x before day; cut companion section if behind |
| Internet fails at venue | Medium | Mobile hotspot + pre-recorded backup always ready |
