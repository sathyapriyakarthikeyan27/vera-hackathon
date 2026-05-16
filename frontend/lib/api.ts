/**
 * VERA backend API client.
 * All calls go through Next.js /api/* rewrite → backend, so no CORS config
 * is needed on the client and the backend URL stays server-side only.
 */

const BASE = "/api";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`VERA API error ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// ── Session ───────────────────────────────────────────────────────────────────

export type Language = "en" | "hi" | "ta";

export interface VERASession {
  session_id: string;
  created_at: string;
  updated_at: string;
  language: Language;
  user_name: string | null;
  risk_assessment: RiskAssessment | null;
  risk_profile: RiskProfile | null;
  schemes_output: SchemesOutput | null;
  education_output: EducationOutput | null;
  companion_output: CompanionOutput | null;
  completed_agents: string[];
}

export async function createSession(language: Language = "en"): Promise<VERASession> {
  return request<VERASession>("/session", {
    method: "POST",
    body: JSON.stringify({ language }),
  });
}

export interface SignupData {
  name: string;
  age_group: string;
  gender: string;
  location: string;
  language: Language;
}

export async function signup(data: SignupData): Promise<{ session_id: string; language: Language; user_name: string }> {
  return request("/session/signup", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getSession(sessionId: string): Promise<VERASession> {
  return request<VERASession>(`/session/${sessionId}`);
}

// ── Risk Profile ──────────────────────────────────────────────────────────────

export interface TimelineEvent {
  year: number;
  event: string;
  status: "completed" | "missed" | "urgent";
}

export interface RiskProfile {
  risk_level: "Low" | "Moderate" | "High" | "Urgent";
  risk_score: number;
  cancer_types_flagged: string[];
  screening_gap_years: number | null;
  timeline: TimelineEvent[];
  plain_language_summary: string;
  disclaimer: string;
}

// ── Scheme Navigator ──────────────────────────────────────────────────────────

export interface Clinic {
  name: string;
  distance_km: number;
  address: string;
  female_doctor_available: boolean;
  cost: "Free" | "Subsidized" | "Paid";
  next_available: string | null;
  contact: string | null;
  appointment_url: string | null;
  services: string[];
}

export interface SchemeMatch {
  scheme_name: string;
  description: string;
  eligibility_summary: string;
  coverage: string;
  url: string | null;
}

export interface SchemesOutput {
  matched_schemes: SchemeMatch[];
  nearest_clinics: Clinic[];
}

// ── Education ─────────────────────────────────────────────────────────────────

export interface EducationSection {
  title: string;
  content: string;
}

export interface EducationOutput {
  video_url: string | null;
  personalized_intro: string;
  text_summary: string;
  language: Language;
  cancer_type: string;
  sections?: EducationSection[];
}

export async function generateEducation(
  sessionId: string
): Promise<EducationOutput> {
  return request<EducationOutput>("/education/generate", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

// ── Companion ─────────────────────────────────────────────────────────────────

export interface FollowUpItem {
  date: string;
  action: string;
  location: string | null;
  contact: string | null;
}

export interface CompanionOutput {
  greeting: string;
  follow_up_plan: FollowUpItem[];
  family_message_drafts: Record<Language, string>;
  reminder_schedule: Array<{ date: string; message: string }>;
}

export async function generateFollowup(
  sessionId: string
): Promise<CompanionOutput> {
  return request<CompanionOutput>("/companion/followup", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function simulateCheckin(
  sessionId: string
): Promise<{ checkin_message: string; simulated_days: number }> {
  return request("/companion/checkin", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

// ── Records Explainer ────────────────────────────────────────────────────────

export interface ClinicalSignals {
  anomalies: string[];
  severity: "high" | "medium" | "low";
  confidence: number;
  specialist_signal: string | null;
  urgency_flag: boolean;
}

export interface RecordExplanation {
  text: string;
  language: Language;
  document_type: string;
}

export interface RecordsOutput {
  explanation: RecordExplanation;
  signals: ClinicalSignals;
  pending_reconciliation: boolean;
}

export interface ReconcileResult {
  reconciled: boolean;
  conflict: boolean;
  original_score: string;
  new_score: string;
  reason: string;
  message: string;
  uncertain?: boolean;
}

export interface RiskAssessmentConflict {
  original_score: string;
  new_score: string;
  reason: string;
  shown_to_user: boolean;
}

export interface RiskAssessment {
  score: string;
  confidence: number;
  source: "profile_only" | "profile+records";
  pending_signals: ClinicalSignals[];
  reconciled: boolean;
  conflict: RiskAssessmentConflict | null;
}

export async function uploadRecord(
  sessionId: string,
  file: File
): Promise<RecordsOutput> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", file);
  const res = await fetch(`${BASE}/records/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`VERA API error ${res.status}: ${body}`);
  }
  return res.json();
}

export async function reconcileRisk(
  sessionId: string
): Promise<ReconcileResult> {
  return request<ReconcileResult>("/risk/reconcile", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

// ── Risk Profiler ─────────────────────────────────────────────────────────────

export interface RiskQuestion {
  id: string;
  question: string;
  type: "text" | "choice" | "number" | "location";
  key: string;
  placeholder?: string;
  optional?: boolean;
  options?: Array<{ value: string; label: string }>;
}

export interface RiskStartResponse {
  question: RiskQuestion;
}

export interface RiskAnswerResponse {
  complete: boolean;
  question?: RiskQuestion;
  risk_profile?: RiskProfile;
}

export async function startRisk(sessionId: string): Promise<RiskStartResponse> {
  return request<RiskStartResponse>("/risk/start", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function answerRisk(
  sessionId: string,
  questionId: string,
  answer: string
): Promise<RiskAnswerResponse> {
  return request<RiskAnswerResponse>("/risk/answer", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, question_id: questionId, answer }),
  });
}

export async function matchSchemes(sessionId: string): Promise<SchemesOutput> {
  return request<SchemesOutput>("/schemes/match", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

// ── Health check ──────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/health");
}
