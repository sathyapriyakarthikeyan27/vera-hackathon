/**
 * VERA backend API client.
 * All calls go through Next.js /api/* rewrite → backend, so no CORS config
 * is needed on the client and the backend URL stays server-side only.
 */

const BASE = "/api";

/** One silent token refresh, shared by concurrent 401s so we never stampede. */
let refreshPromise: Promise<boolean> | null = null;

function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then((res) => res.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retried = false
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    credentials: "include", // send/receive httpOnly auth cookies (same-origin via proxy)
    ...options,
  });

  // Access tokens are short-lived (~15 min). On a 401 mid-session, refresh
  // silently and retry once. Auth endpoints are excluded to avoid loops.
  if (res.status === 401 && !retried && !path.startsWith("/auth/")) {
    if (await refreshOnce()) {
      return request<T>(path, options, true);
    }
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`VERA API error ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// ── Session ───────────────────────────────────────────────────────────────────

export type Language = "en" | "hi" | "ta" | "ar" | "fr" | "es" | "de" | "it" | "ja" | "zh";

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
  language?: Language;
  height_cm?: number;
  weight_kg?: number;
  date_of_birth?: string;
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

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  email_verified: boolean;
  created_at: string | null;
}

export async function authSignup(
  email: string,
  password: string,
  name?: string,
  sessionId?: string,
): Promise<{ user: AuthUser }> {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, name, session_id: sessionId }),
  });
}

export async function authLogin(
  email: string,
  password: string,
  sessionId?: string,
): Promise<{ user: AuthUser }> {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, session_id: sessionId }),
  });
}

export async function authLogout(): Promise<{ ok: boolean }> {
  return request("/auth/logout", { method: "POST" });
}

export async function authMe(): Promise<{ user: AuthUser }> {
  return request("/auth/me");
}

export async function authRefresh(): Promise<{ user: AuthUser }> {
  return request("/auth/refresh", { method: "POST" });
}

export async function linkSession(sessionId: string): Promise<{ ok: boolean }> {
  return request("/auth/link-session", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function requestPasswordReset(email: string): Promise<{ ok: boolean }> {
  return request("/auth/request-reset", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token: string, password: string): Promise<{ ok: boolean }> {
  return request("/auth/reset", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}

export async function verifyEmail(token: string): Promise<{ ok: boolean }> {
  return request("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

/** URL to kick off Google OAuth (full-page redirect, not fetch). */
export function googleLoginUrl(sessionId?: string): string {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  return `/api/auth/google/login${qs}`;
}

// ── Reminders ───────────────────────────────────────────────────────────────

export interface Reminder {
  id: string;
  source: string;
  title: string | null;
  message: string;
  due_at: string;
  status: "pending" | "sent" | "read" | "dismissed" | "failed";
  due: boolean;
}

export interface RemindersResponse {
  reminders: Reminder[];
  unread_due: number;
}

export async function getReminders(): Promise<RemindersResponse> {
  return request<RemindersResponse>("/reminders");
}

export async function markReminderRead(id: string): Promise<{ ok: boolean }> {
  return request(`/reminders/${id}/read`, { method: "POST" });
}

export async function dismissReminder(id: string): Promise<{ ok: boolean }> {
  return request(`/reminders/${id}/dismiss`, { method: "POST" });
}

// ── Notification preferences ──────────────────────────────────────────────────

export interface ChannelOptin {
  in_app: boolean;
  email: boolean;
  sms: boolean;
  whatsapp: boolean;
}

export interface NotificationPreferences {
  channel_optin: ChannelOptin;
  phone_e164: string | null;
  phone_verified: boolean;
  timezone: string;
  quiet_hours_start: number | null;
  quiet_hours_end: number | null;
  consent_at: string | null;
  consent_version: string | null;
}

export interface PreferencesResponse {
  preferences: NotificationPreferences;
  email: string;
  email_verified: boolean;
  consent_version: string;
}

export interface PreferencesPatch {
  channel_optin?: Partial<ChannelOptin>;
  timezone?: string;
  quiet_hours_start?: number | null;
  quiet_hours_end?: number | null;
  give_consent?: boolean;
}

export async function getNotificationPreferences(): Promise<PreferencesResponse> {
  return request<PreferencesResponse>("/notifications/preferences");
}

export async function updateNotificationPreferences(
  patch: PreferencesPatch,
): Promise<PreferencesResponse> {
  return request<PreferencesResponse>("/notifications/preferences", {
    method: "PUT",
    body: JSON.stringify(patch),
  });
}

export async function sendPhoneOtp(phone: string): Promise<{ ok: boolean }> {
  return request("/notifications/phone/send-otp", {
    method: "POST",
    body: JSON.stringify({ phone }),
  });
}

export async function verifyPhoneOtp(code: string): Promise<PreferencesResponse> {
  return request<PreferencesResponse>("/notifications/phone/verify", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
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
  // Provenance (grounded RAG results only). Absent on curated/directory results.
  why_matches?: string;
  source?: "grounded" | "grounded_facts" | "grounded_passage" | "curated" | "directory";
  publisher?: string | null;
  last_verified?: string | null;
  attribution?: string | null;
}

export interface CareDirectory {
  label: string;
  url: string | null;
  note: string;
  attribution?: string | null;
}

export interface SchemesOutput {
  matched_schemes: SchemeMatch[];
  nearest_clinics: Clinic[];
  care_directory?: CareDirectory;
  recommended_specialist?: string;
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
  conflict_context?: {
    triggered: boolean;
    uncertain: boolean;
    original_score: string | null;
    new_score: string | null;
    document_type: string | null;
    document_filename: string | null;
  };
}

export async function generateFollowup(
  sessionId: string
): Promise<CompanionOutput> {
  return request<CompanionOutput>("/companion/followup", {
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
  const send = () =>
    fetch(`${BASE}/records/upload`, {
      method: "POST",
      body: form,
      credentials: "include",
    });
  let res = await send();
  if (res.status === 401 && (await refreshOnce())) {
    res = await send();
  }
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
  why_we_ask?: string;
}

export interface RiskStartResponse {
  question: RiskQuestion;
  total?: number;
}

export interface RiskAnswerResponse {
  complete: boolean;
  question?: RiskQuestion;
  risk_profile?: RiskProfile;
  total?: number;
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
  answer: string,
  key?: string
): Promise<RiskAnswerResponse> {
  return request<RiskAnswerResponse>("/risk/answer", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, question_id: questionId, answer, key }),
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
