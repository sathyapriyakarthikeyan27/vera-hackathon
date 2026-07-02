"use client";

import { useState } from "react";
import Link from "next/link";
import { AuthShell } from "@/components/AuthShell";
import { requestPasswordReset } from "@/lib/api";

const INPUT =
  "w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      await requestPasswordReset(email.trim());
    } catch {
      // Intentionally ignore — we never reveal whether an account exists.
    } finally {
      setSent(true);
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <AuthShell title="Check your email">
        <p className="text-body-md text-on-surface-variant text-center leading-relaxed">
          If an account exists for that email, I have sent a link to reset your password. It
          expires in 1 hour.
        </p>
        <Link
          href="/login"
          className="block text-center text-label-md text-primary font-semibold hover:underline mt-6"
        >
          Back to sign in
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Reset your password" subtitle="I will email you a link to set a new one.">
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
        <button
          type="submit"
          disabled={loading || !email}
          className="w-full bg-primary hover:bg-primary/90 disabled:bg-surface-container-high disabled:text-outline text-on-primary py-3 rounded-full text-label-md font-bold transition-all min-h-[48px]"
        >
          {loading ? "Sending..." : "Send reset link"}
        </button>
      </form>
      <Link
        href="/login"
        className="block text-center text-label-md text-primary hover:underline mt-6"
      >
        Back to sign in
      </Link>
    </AuthShell>
  );
}
