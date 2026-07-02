"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AuthShell } from "@/components/AuthShell";
import { verifyEmail } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Status = "verifying" | "success" | "error";

function VerifyInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<Status>("verifying");
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    if (!token) {
      setStatus("error");
      return;
    }
    verifyEmail(token)
      .then(async () => {
        await refreshUser();
        setStatus("success");
      })
      .catch(() => setStatus("error"));
  }, [token, refreshUser]);

  if (status === "verifying") {
    return (
      <div className="text-center" role="status" aria-live="polite">
        <div className="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" aria-hidden="true" />
        <p className="text-body-md text-on-surface-variant">Confirming your email...</p>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="text-center">
        <span className="material-symbols-outlined text-secondary text-5xl" aria-hidden="true">check_circle</span>
        <p className="text-body-md text-on-surface mt-3 mb-6">Your email is confirmed. Thank you.</p>
        <Link href="/" className="text-label-md text-primary font-semibold hover:underline">
          Continue to VERA
        </Link>
      </div>
    );
  }

  return (
    <div className="text-center">
      <span className="material-symbols-outlined text-error text-5xl" aria-hidden="true">error</span>
      <p className="text-body-md text-on-surface mt-3 mb-6">
        This confirmation link is invalid or has expired.
      </p>
      <Link href="/" className="text-label-md text-primary font-semibold hover:underline">
        Back to home
      </Link>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <AuthShell title="Email confirmation">
      <Suspense fallback={null}>
        <VerifyInner />
      </Suspense>
    </AuthShell>
  );
}
