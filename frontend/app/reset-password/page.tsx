"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthShell } from "@/components/AuthShell";
import { resetPassword } from "@/lib/api";

const INPUT =
  "w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all";

function ResetForm() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading || password.length < 8) return;
    setLoading(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
      setTimeout(() => router.replace("/login"), 2000);
    } catch {
      setError("This reset link is invalid or has expired. Please request a new one.");
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <p className="text-body-md text-on-surface-variant text-center">
        This reset link is missing its token.{" "}
        <Link href="/forgot-password" className="text-primary font-semibold hover:underline">
          Request a new one
        </Link>
        .
      </p>
    );
  }

  if (done) {
    return (
      <p className="text-body-md text-on-surface-variant text-center leading-relaxed">
        Your password has been updated. Taking you to sign in...
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div>
        <label htmlFor="password" className="block text-label-md text-on-surface-variant mb-2">
          New password
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
          aria-describedby="pw-hint"
        />
        <p id="pw-hint" className="text-label-sm text-on-surface-variant/70 mt-2">
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
        disabled={loading || password.length < 8}
        className="w-full bg-primary hover:bg-primary/90 disabled:bg-surface-container-high disabled:text-outline text-on-primary py-3 rounded-full text-label-md font-bold transition-all min-h-[48px]"
      >
        {loading ? "Updating..." : "Set new password"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthShell title="Choose a new password">
      <Suspense fallback={null}>
        <ResetForm />
      </Suspense>
    </AuthShell>
  );
}
