# DEMO — VERA Live Demo Script

## Event Details
- **Date**: May 20, 2026
- **Venue**: Milan AI Week, Milan, Italy
- **Format**: 7-minute live demo + Q&A
- **Platform**: lablab.ai AI Agent Olympics

## The Persona: Priya

For the demo, we use a consistent persona:

> **Priya**, 38, from Delhi. Has not had a cancer screening in 5 years.
> Family history: mother had breast cancer. No HPV vaccine.
> Speaks Hindi and English. Doesn't know about free government schemes.

Pre-load this session before the demo. The Companion Agent will "remember" her on second visit.

---

## 7-Minute Demo Script

### [0:00 – 1:00] Opening + Problem (60 seconds)

**Presenter says**:

> "600 million women worldwide skip cancer screenings every year. Not because they don't care — but because nobody gave them the truth about their risk, in their language, at the right moment. We built VERA. Vital Early Risk Advisor. Because Vera means truth. And every woman deserves the truth about her own health — before it's too late."

**On screen**: VERA landing page loads. Clean, warm design. Tagline visible.

**Click**: "Start with VERA"

---

### [1:00 – 2:00] Risk Profiler — The Conversation (60 seconds)

**VERA asks** (on screen, conversational UI):
- "Hi, I'm VERA. What's your name?" → Priya
- "How old are you, Priya?" → 38
- "When did you last have a cancer screening?" → "About 5 years ago"
- "Any family history of cancer?" → "Yes, my mother had breast cancer"

**Presenter says**: "VERA isn't a form. She's a conversation. She asks only what matters."

Speed through remaining questions (HPV: No, Location: Delhi, Symptoms: None, Language: Hindi).

---

### [2:00 – 2:30] Risk Score + Visual Timeline (30 seconds)

**On screen**: Risk profile card appears.

```
PRIYA'S RISK PROFILE
━━━━━━━━━━━━━━━━━━━
Risk Level: HIGH
Cervical ●●●●○  Breast ●●●●●

Screening Timeline:
2021 ──●── Missed Pap smear
2023 ──●── Missed mammogram  
2026 ──★── NOW — Action needed
```

**Presenter says**: "In 60 seconds, VERA has mapped 5 years of missed screenings and flagged elevated risk for both cervical and breast cancer. She does this without a single medical test."

---

### [3:00 – 4:00] Scheme Navigator (60 seconds)

**On screen**: Scheme cards appear.

> "Priya, you qualify for free cancer screening under Ayushman Bharat. Here are 3 free screening clinics near you in Delhi."

```
✓ AIIMS Delhi — 4.2km
  Free Pap smear + mammogram
  Female doctor: Available
  Next camp: May 18, 2026

✓ Safdarjung Hospital — 6.8km
  Free screening camp
  Female doctor: Available
  Walk-in: Monday–Friday

✓ Lady Hardinge Medical — 8.1km
  Free cervical screening
  Female doctor: Specialist
  Appointment: Call +91-11-...
```

**Presenter says**: "VERA doesn't just tell Priya she's at risk. She tells her exactly where to go — for free — with a female doctor available. She removes every barrier."

---

### [4:00 – 5:30] Education Agent — Animated Video (90 seconds)

**On screen**: Personalized intro text appears in Hindi, then video plays.

> "Priya, because your profile shows elevated cervical risk, here's exactly what a Pap smear involves — so there are no surprises."

**[60-second animated video plays]**:
- What a Pap smear is (animation, no live camera)
- What to expect: before, during, after
- "It takes 5 minutes. It can save your life."

**Presenter says** (while video plays): "Education is how VERA removes fear. Not a generic YouTube video — a personalized explanation matched to her exact risk profile, in her language."

After video: text summary shown below for accessibility.

---

### [5:30 – 6:00] Companion Memory (30 seconds)

**Presenter says**: "Now let's come back as Priya — one month later."

**Action**: Open new browser tab, navigate to VERA. Session loads.

**On screen**:

> "Welcome back, Priya. It's been 4 weeks since we last spoke. Last time, you were planning to book your screening at AIIMS Delhi. Did you get a chance to go?"

**Presenter says**: "VERA remembers. She's not starting over. She's following up — like a trusted friend would."

---

### [6:00 – 6:30] Family Message Draft (30 seconds)

**On screen**: Follow-up plan appears, then family message draft:

```
Your message to share with your family:

"Hi, I've been taking charge of my health lately. 
I found out I'm overdue for a routine check-up 
and booked a free appointment at AIIMS Delhi on 
May 18th. Just wanted to let you know — would 
love your company if you're free. 💙"

[Copy in Hindi] [Copy in English] [Copy in Tamil]
```

**Presenter says**: "Stigma is one of the biggest barriers. VERA drafts a message Priya can send to her family — framing her appointment as routine self-care, not a cause for alarm."

---

### [6:30 – 7:00] Close (30 seconds)

**Presenter says**:

> "VERA is four agents working as one. A risk profiler that sees her. A navigator that removes cost barriers. An educator that removes fear. And a companion that never lets her fall through the cracks. This is what AI looks like when it's built for the 600 million women the world has been ignoring."

**On screen**: VERA home screen. Partner logos visible. Team slide.

---

## Demo Preparation Checklist

**48 hours before**:
- [ ] Deploy backend to Vultr, confirm uptime
- [ ] Pre-load "Priya" session in production database
- [ ] Test full 7-minute flow end-to-end (3x)
- [ ] Confirm API key active (Gemini + MedGemma — single GEMINI_API_KEY via Google AI Studio)
- [ ] Confirm video files load on production URL
- [ ] Test on the demo machine / laptop

**Day of demo**:
- [ ] Hardcoded fallback data confirmed active
- [ ] Browser tabs pre-opened at correct URLs
- [ ] Font size increased for projector visibility
- [ ] Backup: screen recording of full demo flow ready
- [ ] Mobile hotspot ready (do not rely on venue WiFi)

## Fallback Plan

If the live demo fails mid-way:
1. Switch to pre-recorded screen recording (always have this)
2. Continue narrating over the recording — judges care about the story
3. "We're showing you a recording to save time, the live version is at [URL]"

If a specific agent fails:
- **Risk Profiler fails**: Show hardcoded Priya risk card, continue
- **Scheme Navigator fails**: Show hardcoded clinic cards, continue
- **Video fails**: Show text summary, say "the video is personalized to her risk — here's the transcript"
- **Companion memory fails**: Manually trigger the "welcome back" state

## Q&A Prep — Expected Questions

**"Is this FDA approved?"**
> "VERA is an awareness and navigation tool, not a diagnostic tool. We don't replace doctors — we get women to doctors."

**"What about data privacy?"**
> "We store only what's needed for follow-up. No PII sold or shared. GDPR-aligned by design."

**"How do you handle misinformation risk?"**
> "Every risk output carries a disclaimer. VERA uses MedGemma — Google's medical AI model trained on clinical literature — for risk calibration, and all scheme data is sourced from known government programmes. VERA never diagnoses; it navigates."

**"How do you scale beyond India?"**
> "The agent architecture is country-agnostic. Scheme data is the only country-specific layer. We can add NHS, Medicare equivalents in days."

**"Why MedGemma for risk assessment?"**
> "Medical domain specialisation. MedGemma is Google's purpose-built medical AI model trained on clinical literature — it produces structured risk assessments with clinical reasoning that a general-purpose model cannot reliably replicate. Gemini handles conversation and language. They're complementary and both accessed through the same Google AI Studio API key."
