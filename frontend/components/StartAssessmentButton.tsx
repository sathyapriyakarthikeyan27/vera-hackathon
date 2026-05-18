"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function StartAssessmentButton({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  const [href, setHref] = useState("/signup");

  useEffect(() => {
    const sid = localStorage.getItem("vera_session_id");
    const profileComplete = localStorage.getItem("vera_profile_complete");
    const assessmentComplete = localStorage.getItem("vera_assessment_complete");
    if (sid && profileComplete && assessmentComplete) {
      setHref("/risk");
    } else if (sid && profileComplete) {
      setHref("/assessment");
    }
  }, []);

  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
