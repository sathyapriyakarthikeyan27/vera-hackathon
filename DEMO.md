# DEMO — VERA Live Demo Script

## Event Details

| Field | Value |
|-------|-------|
| Date | May 20, 2026 |
| Venue | Milan AI Week, Milan, Italy |
| Format | 7-minute live demo + Q&A |
| Platform | lablab.ai AI Agent Olympics |

---

## The Demo Persona: Arjun

> **Arjun**, 45-54, male, smoker, family history of colorectal cancer, Mumbai.
> No colonoscopy in over 5 years.
> Initial risk: MEDIUM from profile alone.
> Uploads colonoscopy report with abnormal polyp finding.
> Conflict fires — score escalates from MEDIUM to HIGH.
> Agent 2 routes to Gastroenterologist + Ayushman Bharat.

This is the primary demo persona. It demonstrates the conflict detection mechanic — the centrepiece of VERA's collaborative agent architecture.

---

## 7-Minute Demo Flow

### [0:00 to 0:30] Landing page

**On screen**: VERA landing page. Clean, warm design. "Start Your Assessment" button visible.

**Presenter says**: "600 million people skip cancer screenings every year. Not because they do not care — but because no one gave them the right information, at the right moment. We built VERA."

**Click**: "Start Your Assessment"

---

### [0:30 to 1:00] Signup

**On screen**: Signup form — Name, Date of Birth, Gender, Location, Height, Weight.

Fill in Arjun's details. DOB auto-computes age group. Height + weight auto-computes BMI.

**Presenter says**: "No account. No password. Just the basics — and VERA gets to work."

**Click**: "Continue to Assessment"

---

### [1:00 to 2:00] Assessment — AI-generated adaptive questions

**On screen**: Card-based assessment, one question at a time. Progress bar: Step 1 of 6.

Gemini generates each question based on Arjun's profile: gender, age, BMI, location, prior answers.

Questions cover: family history of colorectal cancer (yes), smoking (yes), screening history (no colonoscopy in 5+ years), existing conditions, optional symptoms.

**Presenter says**: "These questions are not a static form. VERA generates each one based on what Arjun has already told her. A 54-year-old male smoker gets different questions than a 30-year-old woman."

---

### [2:00 to 2:30] Risk profile — MEDIUM

**On screen**: Risk result page. MEDIUM risk. Plain-language reasoning visible.

> "I rated your risk as medium because of your family history of colorectal cancer and the fact that you have not had a colonoscopy in over 5 years."

**Presenter says**: "VERA explains why — not just what. The reasoning is plain language, not medical jargon."

---

### [2:30 to 3:30] Agent 2 — Care navigation

**On screen**: Government scheme card (Ayushman Bharat). Specialist recommendation: Gastroenterologist. Nearby screening facilities.

**Presenter says**: "Agent 2 immediately activates. Arjun does not know about Ayushman Bharat. VERA finds it for him, explains his eligibility, and shows him where to go — for free."

---

### [3:30 to 4:30] Agent 3 — Upload colonoscopy report

**On screen**: Records page. Arjun uploads his colonoscopy PDF.

**On screen**: Agent 3 processes the file. Plain-language explanation appears:

> "Your colonoscopy report shows an abnormal polyp in the ascending colon. The polyp was not fully removed during the procedure and requires a follow-up resection..."

**Presenter says**: "Agent 3 reads the report and explains it in plain language. No jargon. But here is where it gets interesting."

---

### [4:30 to 5:00] Conflict card fires

**On screen**: Conflict card appears — visually distinct, different colour.

> "I have updated your risk assessment. Your profile initially pointed to Medium risk. But your colonoscopy report has changed that picture. I now consider your risk to be High. Here is why: your report found an abnormal polyp that was not fully removed and requires urgent follow-up."

**Presenter says**: "This is the collaboration mechanic. Agent 3 extracted clinical signals and wrote them to the shared state. Agent 1 ran in reconcile mode, compared the original score to the new evidence, detected a conflict, and updated the score. The agents are checking each other's conclusions."

---

### [5:00 to 5:30] Updated care plan — HIGH risk

**On screen**: Agent 2 re-activates with HIGH risk. Gastroenterologist shown as urgent referral. Ayushman Bharat scheme highlighted for the specialist visit.

**Presenter says**: "Agent 2 now recalculates for HIGH risk. The same scheme — but now framed as an urgent specialist referral, not routine screening."

---

### [5:30 to 6:00] Companion check-in

**On screen**: "Simulate 3 Days Later" button. Click it.

> "Hi Arjun, it has been a few days since your VERA assessment. You had planned to book with a gastroenterologist. Have you had a chance to take that step? I am here if you need help finding the right clinic."

**Presenter says**: "VERA does not wait for Arjun to come back. She reaches out. This is Agent 4 — the Companion. It fires proactively, personalised to his specific next step."

---

### [6:00 to 6:30] Chat — Q&A about the report

**On screen**: Chat page. Arjun asks: "What does this mean for me?"

VERA responds based on the actual colonoscopy report — not a static answer.

**Presenter says**: "Arjun can ask anything about his report. VERA answers using the actual document context — not a generic response."

---

### [6:30 to 7:00] Close

**Presenter says**: "Four agents working as one. A risk profiler that adapts to each person. A navigator that removes cost barriers. A records explainer that surfaces hidden risk. And a companion that never lets anyone fall through the cracks. This is VERA."

---

## Demo Preparation Checklist

**48 hours before:**
- [ ] Vultr deployment confirmed live at `http://<vultr-ip>`
- [ ] Test full flow end-to-end (3x) with Arjun persona
- [ ] GEMINI_API_KEY confirmed active with gemini-2.5-flash and gemini-2.5-pro
- [ ] Conflict card fires correctly after colonoscopy upload
- [ ] Chat page loads real report context, not static demo text
- [ ] "Simulate 3 Days Later" check-in fires correctly
- [ ] Browser tabs pre-opened: landing, assessment, risk, records, chat

**Day of demo:**
- [ ] Font size increased for projector
- [ ] Screen recording backup of full flow ready
- [ ] Mobile hotspot ready — do not rely on venue WiFi

---

## Fallback Plan

If live demo fails mid-way: switch to pre-recorded screen recording. Continue narrating over it.

| Agent fails | Fallback |
|-------------|---------|
| Risk Profiler | Show hardcoded MEDIUM risk card, continue |
| Care Navigator | Show hardcoded scheme + clinic cards, continue |
| Records upload | Show static explanation text, describe the dual-output mechanic |
| Conflict card | Describe the mechanic verbally, show the conflict card screenshot |
| Companion check-in | Read the check-in message text directly |
| Chat | Show static Q&A, explain that real mode uses session context |

---

## Q&A Prep

**"Is this FDA approved?"**
> "VERA is an awareness and navigation tool, not a diagnostic tool. We do not replace doctors — we get people to the right doctor faster."

**"What about data privacy?"**
> "Health records are processed in memory only. Files are never written to disk, never stored after the response. We show judges the try/finally code pattern explicitly."

**"How do you handle wrong risk scores?"**
> "That is exactly what the conflict detection mechanic addresses. If a user uploads a document that contradicts their initial score, Agent 1 reconciles both sources of evidence and surfaces the conflict to the user with a plain-language explanation."

**"How do you scale beyond India?"**
> "The architecture is country-agnostic. Scheme data is the only country-specific layer — it is seeded in pgvector. Adding NHS or Medicare equivalents is a data operation, not a code change."

**"Why not just one big LLM?"**
> "Separation of concerns. Each agent has a different capability requirement. Agent 1 needs structured risk scoring. Agent 3 needs multimodal document reading with Gemini Pro. Agent 2 needs RAG over a scheme database. One model doing all of this is less reliable and harder to debug in a live demo."
