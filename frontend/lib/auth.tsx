"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  authLogin,
  authLogout,
  authMe,
  authRefresh,
  authSignup,
  type AuthUser,
} from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (email: string, password: string, name?: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** The anonymous VERA session id, so account creation can adopt in-progress work. */
function currentSessionId(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return localStorage.getItem("vera_session_id") ?? undefined;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const loaded = useRef(false);

  const loadUser = useCallback(async () => {
    try {
      const { user } = await authMe();
      setUser(user);
    } catch {
      // Access token may just be expired — try one silent refresh.
      try {
        const { user } = await authRefresh();
        setUser(user);
      } catch {
        setUser(null);
      }
    }
  }, []);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    loadUser().finally(() => setLoading(false));
  }, [loadUser]);

  const login = useCallback(async (email: string, password: string) => {
    const { user } = await authLogin(email, password, currentSessionId());
    setUser(user);
    return user;
  }, []);

  const register = useCallback(
    async (email: string, password: string, name?: string) => {
      const { user } = await authSignup(email, password, name, currentSessionId());
      setUser(user);
      return user;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await authLogout();
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refreshUser: loadUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

/**
 * Guard a client page: redirects to /login (preserving return path) once we know
 * the visitor is unauthenticated. Returns { user, loading } for render gating.
 */
export function useRequireAuth() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading || user) return;
    const next =
      typeof window !== "undefined"
        ? window.location.pathname + window.location.search
        : "/";
    router.replace(`/login?next=${encodeURIComponent(next)}`);
  }, [loading, user, router]);

  return { user, loading };
}
