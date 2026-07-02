"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function StartAssessmentButton({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const [href, setHref] = useState("/register");

  useEffect(() => {
    if (loading) return;
    if (!user) {
      setHref("/register");
      return;
    }
    // Signed in — route by how far they got (profile / assessment tracked locally).
    const profileComplete = localStorage.getItem("vera_profile_complete");
    const assessmentComplete = localStorage.getItem("vera_assessment_complete");
    if (profileComplete && assessmentComplete) setHref("/risk");
    else if (profileComplete) setHref("/assessment");
    else setHref("/signup");
  }, [user, loading]);

  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
