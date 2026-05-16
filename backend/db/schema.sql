-- VERA database schema
-- PostgreSQL with pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;

-- Sessions: JSONB blob per session, all agent outputs stored here
CREATE TABLE IF NOT EXISTS sessions (
    session_id       UUID PRIMARY KEY,
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

CREATE INDEX IF NOT EXISTS idx_sessions_updated    ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_appointments_session ON appointments(session_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date   ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_medications_active  ON medications(session_id, active);
CREATE INDEX IF NOT EXISTS idx_checkin_session     ON checkin_memory(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_scheme_country      ON scheme_data(country);
