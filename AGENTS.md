# AGENTS — VERA Agent Specifications

## Agent Orchestration Model

VERA uses a sequential pipeline with a persistent Companion Agent layer:

```
[Risk Profiler] → [Scheme Navigator] → [Education Agent]
                                              ↕
                              [Companion Agent] (always active)
```

The Companion Agent holds session state and is consulted at every phase. The other 3 agents are invoked in sequence during a user session.

---

## Agent 1: Risk Profiler

### Purpose
Transform a 2-minute conversation into a personalized cancer risk fingerprint. Replace fear and confusion with clarity.

### The 8 Questions

| # | Question | What It Captures |
|---|----------|-----------------|
| 1 | "How old are you?" | Age-based risk bracket |
| 2 | "Has anyone in your immediate family been diagnosed with cancer?" | Hereditary risk |
| 3 | "When did you last have a cancer screening? (Pap smear, mammogram, or similar)" | Screening gap |
| 4 | "Have you received an HPV vaccine?" | HPV risk mitigation |
| 5 | "Do you smoke, or have you smoked in the past?" | Lifestyle risk |
| 6 | "Where do you currently live? (Country, State)" | Scheme eligibility + clinic proximity |
| 7 | "Have you noticed any symptoms recently — like unusual discharge, lumps, or persistent pain?" | Urgency flag (not diagnostic) |
| 8 | "What language would you like VERA to speak with you?" | Multilingual routing |

### Conversation Design
- Questions asked one at a time, conversationally
- Gemini manages the conversation flow — responses can trigger follow-ups
- No clinical jargon in questions
- Empathetic framing: "VERA is here to understand you, not to judge"

### Risk Scoring Logic

MedGemma (medgemma-4b-it) receives the structured patient profile and returns a scored assessment as JSON:

```json
{
  "risk_level": "High",
  "risk_score": 8,
  "cancer_types_flagged": ["cervical", "breast"],
  "screening_gap_years": 5,
  "reasoning": "One sentence clinical reasoning based on the profile.",
  "recommendations": "One sentence on the most important next step."
}
```

Score ranges: Low (0–3) · Moderate (4–6) · High (7–9) · Urgent (10+)

Falls back to deterministic rule-based scoring if MedGemma is unavailable — demo never crashes.

### Output Schema

```json
{
  "risk_level": "Moderate",
  "risk_score": 6,
  "cancer_types_flagged": ["cervical", "breast"],
  "screening_gap_years": 4,
  "timeline": [
    {"year": 2020, "event": "Last known screening", "status": "completed"},
    {"year": 2022, "event": "Recommended Pap smear", "status": "missed"},
    {"year": 2024, "event": "Recommended mammogram", "status": "missed"},
    {"year": 2026, "event": "Now — VERA recommends immediate action", "status": "urgent"}
  ],
  "plain_language_summary": "Based on what you've shared, your cervical cancer risk is moderate. You haven't had a screening in about 4 years, which is longer than recommended. The good news: this is completely fixable.",
  "disclaimer": "This is not a medical diagnosis. VERA provides risk awareness only. Please consult a qualified doctor."
}
```

### Models Used
- **Gemini 2.0 Flash**: Conversation management, question sequencing, plain-language summary generation
- **MedGemma (medgemma-4b-it)**: Medical risk scoring — structured JSON output with risk level, cancer types, screening gap, and clinical reasoning

---

## Agent 2: Scheme Navigator

### Purpose
Remove the cost and awareness barriers in one step. Show her that free help exists, and where to go.

### Matching Logic

```
User location (state/district)
    + Risk level
    + Income signal (optional)
        ↓
Match against scheme database
        ↓
Filter clinics by:
  - Distance from user
  - Female doctor availability
  - Free or subsidized cost
  - Active screening camps
        ↓
Return top 3 clinics + all matched schemes
```

### Scheme Data

Schemes and clinics are determined dynamically by Gemini based on the user's location (state + country). No real government APIs are called — this is a deliberate hackathon decision. Gemini is prompted to identify relevant national programmes (e.g. Ayushman Bharat PM-JAY, NCSP, NHS) and reputable free screening hospitals for the given location, returning structured JSON. Full fallback data is hardcoded for demo stability.

### Clinic Data Schema

```json
{
  "clinic_name": "AIIMS Delhi Cancer Screening Camp",
  "distance_km": 4.2,
  "address": "Ansari Nagar, New Delhi",
  "female_doctor_available": true,
  "cost": "Free",
  "next_camp_date": "2026-05-18",
  "contact": "+91-11-26588500",
  "appointment_url": null,
  "services": ["Pap smear", "Mammogram", "Breast examination"]
}
```

### Output
- Scheme cards (matched, with eligibility plain-language)
- Clinic tiles (3 nearest, sorted by distance)
- CTA: "Book Now" / "Call to Schedule" / "Walk-in Available"

### Models Used
- **Gemini 2.0 Flash**: Location-aware scheme research, clinic identification, eligibility summarization in user's language, and "why this matches you" personalisation

---

## Agent 3: Education Agent

### Purpose
Replace fear of the unknown with understanding. Show her exactly what a screening involves — before she walks in.

### Content Library

| Topic | Duration | Languages |
|-------|----------|-----------|
| BSE (Breast Self-Examination) guide | 60s | EN, HI, TA |
| Pap smear: what to expect | 75s | EN, HI, TA |
| Mammogram: the procedure | 60s | EN, HI, TA |
| Why early detection saves lives | 45s | EN, HI, TA |
| After your screening: next steps | 45s | EN, HI, TA |

### Personalization Logic

```
Risk profile: cervical risk flagged, Hindi language
    ↓
Select: Pap smear video + "Why early detection" video
    ↓
Gemini generates personalized intro: 
  "Priya, because your risk profile shows cervical concern,
   here's exactly what a Pap smear involves..."
    ↓
Assemble: personalized intro text + video segment
    ↓
Output: video player + text summary below
```

### Implementation — Demo Strategy
For the hackathon demo, pre-render or source 2–3 short animated video segments. Gemini generates the personalized script overlay/narration. Full generative video pipeline is a post-hackathon feature.

### Output Schema

```json
{
  "video_url": "/education/pap-smear-hindi.mp4",
  "personalized_intro": "Priya, based on your profile...",
  "text_summary": "A Pap smear takes about 5 minutes...",
  "language": "Hindi",
  "cancer_type": "cervical",
  "follow_up_prompt": "Would you like to see what to expect after your screening?"
}
```

### Models Used
- **Gemini**: Personalized script generation, translation, intro/outro narration text
- **No Featherless needed here** (content generation, not medical reasoning)

---

## Agent 4: Companion Agent

### Purpose
Be the persistent, warm presence that follows up — so no woman falls through the cracks after her first VERA interaction.

### Memory Design

```
Session created → profile stored with session_id
User returns → session_id cookie → profile loaded
Gemini receives: "User is Priya, last session May 12, 
  risk was Moderate, she hadn't booked a clinic yet.
  Greet her warmly and ask how the appointment went."
```

### Follow-Up Plan Generation

Input: full session context
Output:
```
Your VERA Follow-Up Plan
─────────────────────────
✓ This week: Call AIIMS Delhi to confirm your free Pap smear
  📞 +91-11-26588500 | Ask for: free screening camp

✓ May 18: Your screening camp date at AIIMS Delhi

✓ June 12: VERA check-in — How did it go?

✓ Yearly: Set a reminder each May for your annual cervical screening
```

### Family Message Draft

Gemini generates a warm, non-clinical, culturally appropriate message:

```
English version:
"Hi [Name], I've been reading up on women's health and found 
out I'm overdue for a routine check-up. I've made an appointment 
at [Clinic] on [Date] — completely free through a government program. 
Just wanted to let you know. Would love your company if you're free. 💙"

Tamil version:
[Gemini generates culturally appropriate Tamil equivalent]

Hindi version:
[Gemini generates culturally appropriate Hindi equivalent]
```

### Multilingual Support

| Language | Script | Greeting |
|----------|--------|---------|
| English | Latin | "Hi, I'm VERA. I'm here to help you understand your health." |
| Hindi | Devanagari | "नमस्ते, मैं VERA हूँ।" |
| Tamil | Tamil | "வணக்கம், நான் VERA." |

Language detection: user preference from Risk Profiler Q8. Gemini handles translation.

### Output Schema

```json
{
  "greeting": "Welcome back, Priya. Last time we spoke, you were planning to book your screening.",
  "follow_up_plan": [...],
  "family_message_drafts": {
    "english": "...",
    "hindi": "...",
    "tamil": "..."
  },
  "reminder_schedule": [
    {"date": "2026-05-18", "message": "Your screening camp today at AIIMS Delhi"},
    {"date": "2026-06-12", "message": "VERA check-in: How did your appointment go?"}
  ]
}
```

### Models Used
- **Gemini**: All output generation — greeting, follow-up plan, message drafts, multilingual translation
- Memory managed in backend session store, not within the model itself

---

## Inter-Agent Communication

All agents communicate via the orchestration backend. No direct agent-to-agent calls.

```
Frontend → POST /risk/score
Backend  → RiskProfiler.run(session) → returns risk_output
Backend  → SchemeNavigator.run(session, risk_output) → returns schemes
Backend  → EducationAgent.run(session, risk_output) → returns video
Backend  → CompanionAgent.run(session, all_outputs) → returns follow_up
Frontend ← Full session response (streamed or batched)
```

Session object is the shared context bus passed through each agent.
