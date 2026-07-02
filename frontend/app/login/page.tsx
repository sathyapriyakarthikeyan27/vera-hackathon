"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthShell, GoogleButton } from "@/components/AuthShell";
import { useAuth } from "@/lib/auth";
import { googleLoginUrl } from "@/lib/api";

const INPUT =
  "w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all";

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const sessionId =
    typeof window !== "undefined" ? localStorage.getItem("vera_session_id") ?? undefined : undefined;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      router.replace(next);
    } catch {
      setError("Incorrect email or password. Please try again.");
      setLoading(false);
    }
  }

  return (
    <>
      <GoogleButton href={googleLoginUrl(sessionId)} label="Continue with Google" />

      <div className="flex items-center gap-3 my-6" aria-hidden="true">
        <div className="flex-1 h-px bg-outline-variant" />
        <span className="text-label-sm text-on-surface-variant">or</span>
        <div className="flex-1 h-px bg-outline-variant" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <label htmlFor="email" className="block text-label-md text-on-surface-variant mb-2">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={INPUT}
            autoComplete="email"
            required
            aria-required="true"
          />
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="password" className="block text-label-md text-on-surface-variant">
              Password
            </label>
            <Link href="/forgot-password" className="text-label-sm text-primary hover:underline">
              Forgot password?
            </Link>
          </div>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={INPUT}
            autoComplete="current-password"
            required
            aria-required="true"
          />
        </div>

        {error && (
          <p className="text-body-md text-error" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading || !email || !password}
          className="w-full bg-primary hover:bg-primary/90 disabled:bg-surface-container-high disabled:text-outline text-on-primary py-3 rounded-full text-label-md font-bold transition-all min-h-[48px] flex items-center justify-center gap-2"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <p className="text-body-md text-on-surface-variant text-center mt-6">
        New to VERA?{" "}
        <Link href="/register" className="text-primary font-semibold hover:underline">
          Create an account
        </Link>
      </p>
    </>
  );
}

export default function LoginPage() {
  return (
    <AuthShell title="Welcome back" subtitle="Sign in to continue your health journey.">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
