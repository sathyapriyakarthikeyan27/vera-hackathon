"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthShell, GoogleButton } from "@/components/AuthShell";
import { useAuth } from "@/lib/auth";
import { googleLoginUrl } from "@/lib/api";

const INPUT =
  "w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const sessionId =
    typeof window !== "undefined" ? localStorage.getItem("vera_session_id") ?? undefined : undefined;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordTooShort = password.length > 0 && password.length < 8;
  const canSubmit = email.trim() && password.length >= 8 && !loading;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      // Name is collected in onboarding (/signup), not here.
      await register(email.trim(), password);
      // New account has no health profile yet — send them to onboarding.
      router.replace("/signup");
    } catch (e) {
      const msg = String(e);
      setError(
        msg.includes("409")
          ? "An account with this email already exists. Try signing in instead."
          : "Something went wrong. Please check your details and try again.",
      );
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="Your health companion, always in your corner.">
      <GoogleButton href={googleLoginUrl(sessionId)} label="Sign up with Google" />

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
          <label htmlFor="password" className="block text-label-md text-on-surface-variant mb-2">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={INPUT}
            autoComplete="new-password"
            required
            aria-required="true"
            aria-describedby="password-hint"
          />
          <p
            id="password-hint"
            className={`text-label-sm mt-2 ${passwordTooShort ? "text-error" : "text-on-surface-variant/70"}`}
          >
            At least 8 characters.
          </p>
        </div>

        {error && (
          <p className="text-body-md text-error" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full bg-primary hover:bg-primary/90 disabled:bg-surface-container-high disabled:text-outline text-on-primary py-3 rounded-full text-label-md font-bold transition-all min-h-[48px] flex items-center justify-center gap-2"
        >
          {loading ? "Creating account..." : "Create account"}
        </button>
      </form>

      <p className="text-body-md text-on-surface-variant text-center mt-6">
        Already have an account?{" "}
        <Link href="/login" className="text-primary font-semibold hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
