# HACKATHON — AI Agent Olympics at Milan AI Week 2026

## Event Details

| Field | Value |
|-------|-------|
| Event | AI Agent Olympics |
| Conference | Milan AI Week 2026 |
| Platform | lablab.ai |
| Track | Collaborative Agent Swarms |
| Build Phase | May 13–19, 2026 |
| Submission Deadline | May 19, 2026 at 5:00 PM |
| Live Demo | May 20, 2026 — Milan, Italy |

## Our Track: Collaborative Agent Swarms

The Collaborative Agent Swarms track rewards:
- Multiple agents that work together meaningfully
- Clear division of responsibilities between agents
- Emergent capability from collaboration (whole > sum of parts)
- Real-world impact of the multi-agent system

VERA's 4-agent architecture is purpose-built for this track. Each agent has a distinct role. No agent can achieve VERA's mission alone.

---

## Technical Partners

### Google Gemini
- **Why required**: Multimodal understanding, multilingual generation, conversational reasoning
- **Award criteria**: Must demonstrate meaningful Gemini integration beyond basic API calls
- **Our usage**: Risk Profiler conversation, Scheme description generation, Education script personalization, Companion multilingual output
- **Model**: Gemini 2.0 Flash (speed) / Gemini 2.0 Pro (quality)
- **Key requirement**: Show Gemini doing something non-trivial — personalized multilingual output qualifies

### MedGemma
- **Why used**: Google's purpose-built medical AI model, trained on clinical literature
- **Our usage**: Risk score calibration in the Risk Profiler agent — returns structured JSON with risk level, cancer types, and clinical reasoning
- **Model**: `medgemma-4b-it` accessed via Google AI Studio (same GEMINI_API_KEY)
- **Fallback**: Deterministic rule-based scoring if MedGemma is unavailable — demo never crashes

### Vultr
- **Why required**: Backend deployment infrastructure
- **Award criteria**: Backend must actually run on Vultr
- **Our usage**: FastAPI backend deployed on Vultr Cloud Compute
- **Region**: blr1 (Bangalore) for India latency demo
- **Key requirement**: Backend URL must resolve to a Vultr IP; confirm with `curl` before submission

---

## Judging Criteria & How VERA Scores

| Criterion | Weight | VERA's Angle |
|-----------|--------|-------------|
| Model integration effectiveness | High | 3 partners used distinctly; Gemini for language, MedGemma for medical risk scoring, Vultr for infra |
| Presentation clarity | High | 7-minute scripted demo with persona "Priya"; clear problem → solution arc |
| Practical business impact | High | 600M women, real government schemes, real clinics, real barriers addressed |
| Uniqueness and creativity | High | Cancer prevention AI companion targeting underserved women globally; multilingual, longitudinal memory |

---

## Submission Requirements Checklist

### Technical
- [ ] All partners integrated and demonstrable (Gemini, MedGemma, Vultr)
- [ ] Backend deployed and accessible on Vultr
- [ ] GEMINI_API_KEY active and not rate-limited (covers both Gemini and MedGemma)
- [ ] Full end-to-end demo flow works (tested 3x)
- [ ] GitHub repository public and linked

### Content
- [ ] Project name: VERA — Vital Early Risk Advisor
- [ ] Track: Collaborative Agent Swarms
- [ ] Team members listed
- [ ] Demo video (3 minutes max) uploaded — use pre-recorded as backup
- [ ] Project description written (see below)
- [ ] Partner logos credited

### lablab.ai Submission Form Fields
- **Project name**: VERA — Vital Early Risk Advisor
- **Tagline**: The AI companion that gives women the truth about their health
- **Track**: Collaborative Agent Swarms
- **Partners used**: Google Gemini, MedGemma, Vultr
- **GitHub URL**: [to be added]
- **Demo URL**: [to be added]
- **Demo video**: [upload pre-recorded walkthrough]

---

## Project Description (for submission)

> 600 million women skip cancer screenings every year — not because they don't care, but because no one gave them the truth about their risk, in their language, at the right moment.
>
> VERA (Vital Early Risk Advisor) is a 4-agent AI companion for women's cancer prevention. In one 7-minute conversation, VERA:
>
> - **Risk Profiler Agent**: Assesses personalized cancer risk through 8 conversational questions, producing a risk score and visual screening timeline (Gemini conversation + MedGemma medical risk scoring)
> - **Scheme Navigator Agent**: Matches the user to free government health programs and finds the 3 nearest free screening clinics with female doctors (Gemini, location-aware)
> - **Education Agent**: Generates a personalized animated video explaining exactly what a screening involves — in her language, matched to her risk type (Gemini)
> - **Companion Agent**: Remembers her across sessions, drafts a family message to overcome social stigma, and creates a follow-up plan so she never falls through the cracks (Gemini, multilingual: English, Hindi, Tamil)
>
> Built on Google Gemini, MedGemma (Google's medical AI model), and deployed on Vultr. VERA is not a diagnostic tool — she's the bridge between risk and action.
>
> In India, 70% of cervical cancer cases are detected at Stage 3 or 4. VERA exists to change that number.

---

## Timeline — Build Week

| Day | Date | Goal |
|-----|------|------|
| Day 1 | May 13 | Repo setup, frontend skeleton, backend scaffold, API keys |
| Day 2 | May 14 | Risk Profiler agent: Gemini conversation + MedGemma risk scoring |
| Day 3 | May 15 | Scheme Navigator: seed data + matching logic + clinic cards |
| Day 4 | May 16 | Education Agent: video assets + Gemini personalization |
| Day 5 | May 17 | Companion Agent: session memory + follow-up + family message |
| Day 6 | May 18 | Full integration, demo flow polish, Vultr deployment |
| Day 7 | May 19 | Bug fixes, demo rehearsal, submission by 5PM |
| Demo Day | May 20 | Live presentation — Milan |

---

## Team Roles

| Role | Responsibility |
|------|---------------|
| Technical Developer (you) | Full-stack lead, all implementation, Claude Code primary |
| Developer Leader | Technical architecture decisions, code review |
| Developer/Designer | Frontend UI/UX, demo visuals, video assets |
| Project Manager | Timeline, submission form, coordination |
| Business Project Manager | Pitch narrative, judging criteria alignment, demo script |

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| MedGemma availability / quota | Low | Rule-based fallback always active; demo never depends on MedGemma exclusively |
| Gemini rate limits during demo | Low | Use cached responses for demo; separate demo API key |
| Vultr deployment fails | Low | Keep local fallback running; deploy by Day 6 |
| Video pipeline too complex | Medium | Use pre-rendered segments; Gemini provides narration text only |
| Demo overruns 7 minutes | Medium | Practice 5x before day; cut Education video to 45s if needed |
| Internet fails at venue | Medium | Mobile hotspot + pre-recorded backup always ready |
