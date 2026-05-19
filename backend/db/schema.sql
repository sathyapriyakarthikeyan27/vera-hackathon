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
