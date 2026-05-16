/**
 * Browser-side session helpers.
 * Session ID is stored in localStorage so it persists across page refreshes
 * and tabs — giving the Companion Agent its "returning user" capability.
 */

import { createSession, getSession, type Language, type VERASession } from "./api";

const SESSION_KEY = "vera_session_id";

export async function getOrCreateSession(
  language: Language = "en"
): Promise<VERASession> {
  const existingId = localStorage.getItem(SESSION_KEY);

  if (existingId) {
    try {
      const session = await getSession(existingId);
      return session;
    } catch {
      // Session expired or not found — create a new one
      localStorage.removeItem(SESSION_KEY);
    }
  }

  const session = await createSession(language);
  localStorage.setItem(SESSION_KEY, session.session_id);
  return session;
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

export function getSavedSessionId(): string | null {
  return localStorage.getItem(SESSION_KEY);
}
