# Reminders & Notifications — Implementation Plan

Last updated: 2026-07-01

Status: **Approved, phased build in progress.** Phase 0 (auth) first.

---

## 1. Motivation

Today "reminders" are display-only. Gemini generates a `reminder_schedule`
(`[{date, message}]`) inside `companion_output`, cached on the session row, and
the frontend renders the whole array inline on `/companion`. There is:

- No scheduling (no `BackgroundTasks`, no cron, nothing time-based).
- No persistence as individual reminders (the `appointments` / `medications`
  tables in `schema.sql` are dormant — never read or written).
- No delivery (reminders are never sent anywhere).

We want real reminders: persisted, scheduled, delivered across **in-app, email,
SMS, and WhatsApp**, surfaced via a **bell in the global Navbar + a banner** for
the single most-urgent item, with the inline list removed from `/companion`.

---

## 2. Decisions (locked)

| # | Decision | Notes |
|---|----------|-------|
| 1 | **Production-grade auth** replaces localStorage-only sessions | Email+password (Argon2) **+ Google OAuth**, email verification, JWT access+refresh in httpOnly cookies. Gives the durable `user_id` that day-later reminders require. |
| 2 | **Free providers** | Email: Resend or SendGrid free tier. SMS + WhatsApp: **Twilio** free trial / WhatsApp sandbox. |
| 3 | **Celery + Celery Beat** for scheduling & delivery | Redis (already present) becomes the broker. Reverses the "drop Celery" and "Redis never a broker" decisions — docs updated accordingly. |
| 4 | **Notification Preferences prompted after `/risk`** | Non-blocking card on the results page + permanent entry from the bell/settings. Captured before the companion plan generates reminders. |
| 5 | Bell + banner combo, bell in the **global Navbar** | Bell badge = due+unread in-app count. Banner reserved for the single most-urgent overdue item or a risk-escalation conflict. |

### Reversed decisions (update in DECISIONS.md / CLAUDE.md)
- ~~Drop Celery / no external task queue~~ → **Celery + Beat adopted** for durable
  scheduled multi-channel delivery with retries.
- ~~Redis is a cache only, never a Celery broker~~ → **Redis is now dual-purpose:**
  cache-aside (LLM results) **and** Celery broker/result backend. Keep logical DB
  separation (e.g. cache on db 0, broker on db 1).
- ~~Session persistence via localStorage (full auth on roadmap)~~ → **Full auth
  implemented** (email+password + Google OAuth).

---

## 3. Architecture

### 3.1 Auth (Phase 0)
- `users`: `id, email (unique, citext), password_hash (nullable for OAuth-only),
  email_verified, name, created_at`.
- `oauth_accounts`: `user_id, provider ('google'), provider_account_id, created_at`.
- `auth_tokens` (existing, repurposed): refresh-token + email-verification +
  password-reset tokens (hashed, single-use, expiring).
- Password hashing: Argon2id (`argon2-cffi`).
- Tokens: short-lived access JWT (~15m) + long-lived refresh JWT (~30d) in
  **httpOnly, Secure, SameSite=Lax cookies**. Refresh rotation + revocation list.
- Google OAuth: Authorization Code flow. `GET /auth/google/login` → redirect;
  `GET /auth/google/callback` → create/link user, verify email implicitly, set cookies.
- Email verification + password reset via the email channel (reuses Phase 4 sender).
- `sessions.user_id` linked; existing session data migrates under the account.
- Frontend: replace the localStorage-only routing gate (`StartAssessmentButton`)
  with real auth state; add login/signup/verify/reset pages; protect routes.

### 3.2 Data model (Phase 1)
- `reminders`: `id, user_id, session_id, source (companion|appointment|medication),
  title, message, due_at (timestamptz), status (pending|scheduled|sent|read|dismissed|failed),
  channels (text[]), created_at, sent_at, read_at, attempts, last_error, dedupe_key`.
  - `dedupe_key = hash(user_id, source, due_at, message)` — regenerating the
    companion plan must not duplicate rows.
- `notification_preferences`: `user_id, email, phone_e164, whatsapp_e164,
  channel_optin (jsonb: {in_app, email, sms, whatsapp}), consent_at, consent_version,
  email_verified, phone_verified, timezone, quiet_hours_start, quiet_hours_end`.
  - Contact fields are **PII: encrypted at rest, never logged, never cached.**
- The dormant `appointments` / `medications` tables become **producers** of
  `reminders` rows rather than parallel systems.

### 3.3 Scheduling & delivery (Phase 2)
- **Celery Beat** periodic task (every ~60s) claims due rows
  (`status='pending' AND due_at <= now()`) using `SELECT … FOR UPDATE SKIP LOCKED`,
  enqueues a delivery task per reminder, marks `scheduled`.
- **Celery worker** delivery task: resolve enabled+consented channels from
  `notification_preferences`, respect timezone + quiet hours, fan out to channel
  adapters, mark `sent`/`failed`, retry with exponential backoff (max N).
- docker-compose gains `celery-worker` and `celery-beat` services (same image as
  backend, different command). Redis broker via `REDIS_URL` (broker db) — cache
  stays on its own db.

### 3.4 Channel adapters (Phases 4–6)
Common interface `Channel.send(reminder, contact) -> Result`:
- `in_app` — always on; no external send (bell reads DB).
- `email` — Resend/SendGrid; verified from-domain; unsubscribe link.
- `sms` — Twilio; E.164; unsubscribe (STOP) handling.
- `whatsapp` — Twilio WhatsApp sandbox first, then approved templates; requires
  proven opt-in; cannot send free-form outside the 24h window.
All fail-open with bounded retry; provider outage never crashes the worker; logs
carry no PII.

### 3.5 Frontend
- Bell in shared `<Navbar />` (badge = due+unread in-app). Dropdown lists reminders
  (due first) with mark-read / dismiss.
- Banner: single most-urgent overdue reminder **or** risk-escalation conflict.
- **Remove** the inline reminder timeline from `/companion` → greeting → action
  plan → family message only.
- Notification Preferences: card after `/risk` + full settings screen (channels,
  contact, consent, timezone, quiet hours, unsubscribe).
- Auth pages: login, signup, Google button, email-verify, password-reset.

### 3.6 New/changed endpoints
- Auth: `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`,
  `POST /auth/refresh`, `GET /auth/me`, `POST /auth/verify-email`,
  `POST /auth/request-reset`, `POST /auth/reset`, `GET /auth/google/login`,
  `GET /auth/google/callback`.
- Reminders: `GET /reminders`, `POST /reminders/{id}/read`,
  `POST /reminders/{id}/dismiss`.
- Preferences: `GET /notifications/preferences`, `PUT /notifications/preferences`,
  plus email/phone verification endpoints.

### 3.7 Config / secrets (`.env.example`)
- `JWT_SECRET`, `ACCESS_TOKEN_TTL`, `REFRESH_TOKEN_TTL`, `COOKIE_DOMAIN`.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.
- `EMAIL_PROVIDER`, `EMAIL_API_KEY`, `EMAIL_FROM`.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_FROM`,
  `TWILIO_WHATSAPP_FROM`.
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (Redis dbs), `APP_BASE_URL`.

---

## 4. Phasing

| Phase | Deliverable | Ships value |
|-------|-------------|-------------|
| **0** | Production auth (email+pw + Google OAuth, JWT cookies, verification), link `sessions.user_id`, new frontend auth flow, doc updates | Real accounts + durable identity |
| **1** | Reminders schema + materialize + Bell + Banner + read/dismiss + remove inline list (in-app only) | **Fixes the companion page UX** |
| **2** | Celery + Beat + Redis broker; scheduled dispatch + retries; compose services | Reminders actually fire |
| **3** | Notification Preferences (after `/risk`) + contact/consent + email/phone verification | Users choose channels |
| **4** | Email channel | First external delivery |
| **5** | SMS via Twilio | |
| **6** | WhatsApp via Twilio (sandbox → templates) | Hardest, last |

Each phase is independently shippable and verifiable.

---

## 5. Risks & notes
- **Auth is the gate** — day-later reminders need durable identity; everything
  waits on Phase 0.
- **PII expansion** — collecting email/phone changes the privacy posture; encrypt
  at rest, exclude from logs and from the LLM cache; explicit per-channel consent
  (WhatsApp/Meta legally require opt-in proof; email/SMS need unsubscribe).
- **Timezone** is newly required (avoid 3am sends); collected in preferences.
- **Multi-worker safety** — claim rows with `FOR UPDATE SKIP LOCKED`.
- **WhatsApp lead time** — template approval + opt-in; start on the free sandbox.
- **Cost** — Twilio trial credits are finite; document limits.
