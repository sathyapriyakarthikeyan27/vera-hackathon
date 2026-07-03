-- VERA database schema
-- PostgreSQL with pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;

-- Users: persistent identity, linked to auth tokens and sessions
CREATE TABLE IF NOT EXISTS users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email        VARCHAR(255) UNIQUE NOT NULL,
    name         VARCHAR(255),
    age_group    VARCHAR(20),
    gender       VARCHAR(20),
    location     VARCHAR(255),
    language     VARCHAR(10) NOT NULL DEFAULT 'en',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auth tokens: OTP codes and JWT session tokens
-- token_type = 'otp' for email OTP codes (10-min TTL)
-- token_type = 'session' for JWT jti references (30-day TTL)
CREATE TABLE IF NOT EXISTS auth_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(255) NOT NULL,
    token_type   VARCHAR(20) NOT NULL CHECK (token_type IN ('otp', 'session')),
    expires_at   TIMESTAMPTZ NOT NULL,
    used         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_tokens_user   ON auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expiry ON auth_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_users_email        ON users(email);

-- Production auth additions (email+password + Google OAuth). Idempotent.
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash  VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Broaden auth_tokens types: add refresh / email_verify / password_reset.
ALTER TABLE auth_tokens DROP CONSTRAINT IF EXISTS auth_tokens_token_type_check;
ALTER TABLE auth_tokens ADD CONSTRAINT auth_tokens_token_type_check
    CHECK (token_type IN ('otp', 'session', 'refresh', 'email_verify', 'password_reset'));
CREATE INDEX IF NOT EXISTS idx_auth_tokens_lookup ON auth_tokens(token_hash, token_type);

-- OAuth provider accounts linked to a user
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider            VARCHAR(50) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_account_id)
);
CREATE INDEX IF NOT EXISTS idx_oauth_user ON oauth_accounts(user_id);

-- Sessions: JSONB blob per session, all agent outputs stored here
CREATE TABLE IF NOT EXISTS sessions (
    session_id       UUID PRIMARY KEY,
    user_id          UUID REFERENCES users(id) ON DELETE SET NULL,
    language         VARCHAR(10) NOT NULL DEFAULT 'en',
    user_name        VARCHAR(255),
    risk_state       JSONB,
    risk_assessment  JSONB,
    risk_profile     JSONB,
    schemes_output   JSONB,
    education_output JSONB,
    companion_output JSONB,
    completed_agents TEXT[] NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Appointments: Agent 4 follow-up reminders
CREATE TABLE IF NOT EXISTS appointments (
    id                   SERIAL PRIMARY KEY,
    session_id           UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    specialist_name      VARCHAR(255) NOT NULL,
    appointment_date     DATE NOT NULL,
    notes                TEXT,
    reminder_sent_3days  BOOLEAN NOT NULL DEFAULT FALSE,
    reminder_sent_day_of BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Medications: Agent 4 post-diagnosis reminders
CREATE TABLE IF NOT EXISTS medications (
    id              SERIAL PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    medication_name VARCHAR(255) NOT NULL,
    dosage          VARCHAR(100),
    frequency       VARCHAR(100),
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Reminders: Agent 4 notifications (in-app now; email/SMS/WhatsApp in later phases).
-- Materialized from companion_output.reminder_schedule; deduped by dedupe_key.
CREATE TABLE IF NOT EXISTS reminders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id  UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    source      VARCHAR(30) NOT NULL DEFAULT 'companion',
    title       VARCHAR(255),
    message     TEXT NOT NULL,
    due_at      TIMESTAMPTZ NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'scheduled', 'sent', 'read', 'dismissed', 'failed')),
    channels    TEXT[] NOT NULL DEFAULT '{in_app}',
    dedupe_key  VARCHAR(64) UNIQUE,
    attempts    INT NOT NULL DEFAULT 0,
    last_error  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at     TIMESTAMPTZ,
    read_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, due_at);
CREATE INDEX IF NOT EXISTS idx_reminders_due  ON reminders(status, due_at);

-- Add 'scheduled' status to reminders created before Celery dispatch existed.
ALTER TABLE reminders DROP CONSTRAINT IF EXISTS reminders_status_check;
ALTER TABLE reminders ADD CONSTRAINT reminders_status_check
    CHECK (status IN ('pending', 'scheduled', 'sent', 'read', 'dismissed', 'failed'));

-- Notification preferences: per-user channel opt-in, contact, consent, timezone.
-- Email channel uses the account email (users.email / users.email_verified);
-- phone is verified here via OTP. PII (phone) — never logged, never cached.
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id           UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    channel_optin     JSONB NOT NULL DEFAULT '{"in_app": true, "email": false, "sms": false, "whatsapp": false}',
    phone_e164        VARCHAR(20),
    phone_verified    BOOLEAN NOT NULL DEFAULT FALSE,
    timezone          VARCHAR(64) NOT NULL DEFAULT 'UTC',
    quiet_hours_start SMALLINT,
    quiet_hours_end   SMALLINT,
    consent_at        TIMESTAMPTZ,
    consent_version   VARCHAR(20),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Checkin memory: Agent 4 persistent health timeline with pgvector
CREATE TABLE IF NOT EXISTS checkin_memory (
    id         SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role       VARCHAR(20) NOT NULL CHECK (role IN ('user', 'vera')),
    content    TEXT NOT NULL,
    embedding  vector(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Scheme data: Agent 2 mock RAG — government schemes and clinics
CREATE TABLE IF NOT EXISTS scheme_data (
    id          SERIAL PRIMARY KEY,
    scheme_name VARCHAR(255) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    cancer_types TEXT[] NOT NULL DEFAULT '{}',
    content     TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    embedding   vector(768),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add records_output column if it was not in the original CREATE TABLE
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS records_output JSONB;

CREATE INDEX IF NOT EXISTS idx_sessions_updated    ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_appointments_session ON appointments(session_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date   ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_medications_active  ON medications(session_id, active);
CREATE INDEX IF NOT EXISTS idx_checkin_session     ON checkin_memory(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_scheme_country      ON scheme_data(country);

-- ─────────────────────────────────────────────────────────────────────────────
-- RAG corpus (Agent 2 real-source pipeline). Distinct from the legacy synthetic
-- scheme_data above. Three tables, by design:
--   source_documents — registry of real, licensed sources + freshness bookkeeping
--   scheme_chunks     — chunked narrative text + embeddings (the "retrieve" corpus)
--   scheme_facts      — safety-critical structured facts, gated on human sign-off
-- The narrative goes to RAG; the numbers a wrong answer could harm someone with
-- live in scheme_facts and are never surfaced until verified = TRUE.
-- ─────────────────────────────────────────────────────────────────────────────

-- Registry of every real source we ingest, with licensing + freshness tracking.
CREATE TABLE IF NOT EXISTS source_documents (
    id             SERIAL PRIMARY KEY,
    source_key     VARCHAR(120) UNIQUE NOT NULL,   -- stable id, e.g. 'uk_nhs_cervical_screening'
    title          VARCHAR(255) NOT NULL,
    url            TEXT NOT NULL,
    jurisdiction   VARCHAR(100) NOT NULL,          -- 'UK', 'India', 'Egypt'
    source_type    VARCHAR(20)  NOT NULL,          -- 'html' | 'pdf'
    publisher      VARCHAR(255) NOT NULL,          -- 'NHS', 'GOV.UK (UKHSA)'
    license        VARCHAR(120) NOT NULL,          -- 'OGL-v3.0' (must be reuse-permitted)
    cancer_types   TEXT[] NOT NULL DEFAULT '{}',
    content_hash   VARCHAR(64),                    -- sha256 of normalized extracted text
    published_date DATE,                           -- source's own "last reviewed" date if available
    last_fetched   TIMESTAMPTZ,
    last_verified  TIMESTAMPTZ,                    -- last time a human/auto pass confirmed the content
    status         VARCHAR(20) NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'active', 'pending_review', 'stale', 'error')),
    last_error     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_source_jurisdiction ON source_documents(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_source_status       ON source_documents(status);

-- Chunked narrative text + embeddings. This is the corpus the retriever searches.
-- tsv is a generated column so hybrid (dense + full-text) search needs no app code
-- to keep it in sync.
CREATE TABLE IF NOT EXISTS scheme_chunks (
    id             SERIAL PRIMARY KEY,
    source_id      INTEGER NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    chunk_index    INTEGER NOT NULL,
    heading        TEXT,
    content        TEXT NOT NULL,
    token_estimate INTEGER,
    embedding      vector(768),                    -- text-embedding-004, RETRIEVAL_DOCUMENT
    tsv            tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_scheme_chunks_source ON scheme_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_scheme_chunks_tsv    ON scheme_chunks USING GIN (tsv);
-- NB: the HNSW vector index is created by rag_store.ensure_rag_indexes(), not here,
-- so an older pgvector (no HNSW support) degrades to a sequential scan instead of
-- breaking startup.

-- Safety-critical structured facts. Auto-extracted as verified = FALSE, and never
-- surfaced to users until a human signs off. This is the gate that stops a changed
-- eligibility age from reaching users unreviewed.
CREATE TABLE IF NOT EXISTS scheme_facts (
    id               SERIAL PRIMARY KEY,
    source_id        INTEGER REFERENCES source_documents(id) ON DELETE SET NULL,
    jurisdiction     VARCHAR(100) NOT NULL,
    programme        VARCHAR(255) NOT NULL,        -- 'NHS Cervical Screening Programme'
    cancer_type      VARCHAR(50)  NOT NULL,        -- 'cervical'
    sex              VARCHAR(20)  NOT NULL DEFAULT 'all',   -- 'female' | 'male' | 'all'
    eligible_age_min INTEGER,
    eligible_age_max INTEGER,
    interval_months  INTEGER,                      -- screening interval, null if n/a
    cost             VARCHAR(50),                  -- 'free'
    method           VARCHAR(255),                 -- 'HPV primary screening', 'FIT home kit'
    notes            TEXT,
    verified         BOOLEAN NOT NULL DEFAULT FALSE,  -- human sign-off gate
    verified_by      VARCHAR(255),
    verified_at      TIMESTAMPTZ,
    source_url       TEXT,
    content_hash     VARCHAR(64),                  -- hash of the source chunk this was drawn from
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_scheme_facts_lookup   ON scheme_facts(jurisdiction, cancer_type);
CREATE INDEX IF NOT EXISTS idx_scheme_facts_verified ON scheme_facts(verified);
