"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSession } from "@/lib/api";
import type { VERASession, RiskProfile, RiskAssessmentConflict } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

const MOCK = false; // set to true to use mock data

const MOCK_SESSION: import("@/lib/api").VERASession = {
  session_id: "mock",
  created_at: "",
  updated_at: "",
  language: "en",
  user_name: "Alex",
  risk_assessment: null,
  schemes_output: null,
  education_output: null,
  companion_output: null,
  completed_agents: [],
  risk_profile: {
    risk_level: "Moderate",
    risk_score: 7,
    cancer_types_flagged: ["colorectal", "lung"],
    screening_gap_years: 4,
    timeline: [],
    plain_language_summary: "Your profile shows moderate risk based on your family history and smoking history. I recommend scheduling a screening in the next few months.",
    disclaimer: "This is not a medical diagnosis. VERA provides risk awareness only. Please consult a qualified doctor.",
  },
};

type RiskLevel = "Low" | "Moderate" | "High" | "Urgent";


const RISK_CONFIG: Record<RiskLevel, {
  ringColor: string;
  textColor: string;
  badgeBg: string;
  badgeText: string;
  label: string;
  subtitle: string;
  icon: string;
}> = {
  Low: {
    ringColor: "border-secondary",
    textColor: "text-secondary",
    badgeBg: "bg-secondary-container",
    badgeText: "text-on-secondary-container",
    label: "Low Risk",
    subtitle: "Optimal Range",
    icon: "check_circle",
  },
  Moderate: {
    ringColor: "border-tertiary",
    textColor: "text-tertiary",
    badgeBg: "bg-tertiary-fixed/40",
    badgeText: "text-on-tertiary-fixed",
    label: "Moderate Risk",
    subtitle: "Monitor Closely",
    icon: "warning",
  },
  High: {
    ringColor: "border-error",
    textColor: "text-error",
    badgeBg: "bg-error-container",
    badgeText: "text-on-error-container",
    label: "High Risk",
    subtitle: "Action Recommended",
    icon: "priority_high",
  },
  Urgent: {
    ringColor: "border-error",
    textColor: "text-error",
    badgeBg: "bg-error-container",
    badgeText: "text-on-error-container",
    label: "Urgent",
    subtitle: "Seek Care Now",
    icon: "emergency",
  },
};


interface ExtendedRiskProfile extends RiskProfile {
  ai_reasoning?: string;
}

export default function RiskPage() {
  const [session, setSession] = useState<VERASession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (MOCK) {
        setSession(MOCK_SESSION as import("@/lib/api").VERASession);
        setLoading(false);
        return;
      }
      const sid = localStorage.getItem("vera_session_id");
      if (!sid) {
        setError("No session found. Please start from the beginning.");
        setLoading(false);
        return;
      }
      try {
        const s = await getSession(sid);
        setSession(s);
      } catch {
        setError("Could not load your risk profile. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <p className="text-body-md text-on-surface-variant">Loading your results...</p>
        </div>
      </div>
    );
  }

  if (error || !session?.risk_profile) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6">
        <div className="text-center max-w-sm">
          <p className="text-body-md text-on-surface-variant mb-6">
            {error ?? "Your risk profile is not ready yet."}
          </p>
          <Link href="/assessment" className="text-label-md text-primary font-semibold hover:underline">
            Return to assessment
          </Link>
        </div>
      </div>
    );
  }

  const profile = session.risk_profile as ExtendedRiskProfile;
  const riskLevel: RiskLevel = profile.risk_level in RISK_CONFIG
    ? profile.risk_level as RiskLevel
    : "Moderate";
  const config = RISK_CONFIG[riskLevel];

  return (
    <div className="min-h-screen bg-background">

      <Navbar />

      <main className="pt-32 pb-stack-lg max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop">

        {/* Hero */}
        <section className="mb-stack-lg text-center md:text-left">
          <h1 className="text-headline-lg md:text-headline-xl text-primary mb-4">
            Your Health Assessment Summary
          </h1>
          <p className="text-body-lg text-on-surface-variant max-w-2xl">
            {session.user_name ? `${session.user_name}, based` : "Based"} on your answers, I've analysed your risk factors and prepared a personalised guidance plan for you.
          </p>
        </section>

        {/* Conflict card — the centrepiece, shown only when Agent 3 escalated the score */}
        {session.risk_assessment?.conflict && (
          <ConflictCard conflict={session.risk_assessment.conflict} className="mb-stack-lg" />
        )}

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-gutter">

          {/* Left — Risk gauge */}
          <div className="md:col-span-5 bg-surface-container-lowest rounded-2xl p-stack-md soft-elevation border border-outline-variant flex flex-col items-center justify-center text-center">
            <p className="text-label-md text-on-surface-variant uppercase tracking-widest mb-6">Overall Risk Level</p>

            {/* Circular ring */}
            <div className="relative w-48 h-48 flex items-center justify-center mb-6">
              <div className="absolute inset-0 rounded-full border-[12px] border-surface-container" />
              <div className={`absolute inset-0 rounded-full border-[12px] ${config.ringColor} border-t-transparent border-l-transparent transform -rotate-45`} />
              <div className="flex flex-col items-center gap-1">
                <span
                  className={`material-symbols-outlined text-4xl ${config.textColor}`}
                  style={{ fontVariationSettings: "'FILL' 1" }}
                  aria-hidden="true"
                >
                  {config.icon}
                </span>
                <span className={`text-headline-lg-mobile font-bold ${config.textColor}`}>
                  {config.label.split(" ")[0]}
                </span>
                <span className="text-label-sm text-on-surface-variant">{config.subtitle}</span>
              </div>
            </div>

            {/* Risk badge */}
            <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-label-md font-semibold mb-6 ${config.badgeBg} ${config.badgeText}`}>
              {config.label}
            </span>

            {/* Cancer types flagged */}
            {profile.cancer_types_flagged.length > 0 && (
              <div className="w-full mb-6">
                <p className="text-label-sm text-on-surface-variant uppercase tracking-widest mb-3">Areas to Monitor</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {profile.cancer_types_flagged.map((t) => (
                    <span
                      key={t}
                      className="px-3 py-1.5 bg-primary-fixed/20 text-primary rounded-full text-label-sm capitalize"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <p className="text-body-md text-on-surface-variant italic leading-relaxed">
              &ldquo;{profile.plain_language_summary}&rdquo;
            </p>
          </div>

          {/* Right — Recommendations + Timeline + Reasoning */}
          <div className="md:col-span-7 space-y-gutter">

            {/* Recommendations */}
            <div className="bg-surface-container-lowest rounded-2xl p-stack-md soft-elevation border border-outline-variant">
              <h2 className="text-headline-md text-primary mb-stack-md flex items-center gap-2">
                <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }} aria-hidden="true">lightbulb</span>
                What I Recommend
              </h2>
              <div className="space-y-4">
                <RecommendationItem
                  icon="calendar_today"
                  title={riskLevel === "Low" ? "Schedule a Routine Screening" : "Book an Appointment Soon"}
                  body={
                    riskLevel === "Low"
                      ? "A biannual check-up is enough to keep your baseline on track."
                      : "Please book with a specialist as soon as you can. I'll help you find one nearby."
                  }
                />
{profile.cancer_types_flagged.length > 0 && (
                  <RecommendationItem
                    icon="clinical_notes"
                    title={`Consult a Specialist — ${profile.cancer_types_flagged[0]}`}
                    body="A specialist can give you a clearer picture based on your specific risk factors."
                  />
                )}
              </div>
            </div>

          </div>

          {/* Bottom — Schemes */}
          <div className="md:col-span-8 bg-surface-container-lowest rounded-2xl p-stack-md soft-elevation border border-outline-variant">
            <h2 className="text-headline-md text-primary mb-stack-md">Available Screening Schemes</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {schemesForLocation((session as any)?.risk_state?.answers?.location ?? "").map((s) => (
                <SchemeItem key={s.name} name={s.name} tag={s.tag} body={s.body} />
              ))}
            </div>
          </div>

          {/* Bottom — Hospital CTA with image */}
          <div className="md:col-span-4 relative group overflow-hidden rounded-2xl min-h-[300px] flex items-end">
            <img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDC_N-0AAeBq8U-HhhPgG_KMsflc8nuLXvwuOfaFZGWt1C9rmZHvdfHStgpFL3cjgrjO_XUWVq858iqP_v2Wq764UId5h3826Q98w--YWmgdO5kPV4S5-9uOksNddIYy67nlm41IB9e6w6jyC84FwRMh2klTwKTiLWKQhMAy7Vl7Wdtb_3y178JG3-M0dNpMbdy_w2VbTOwEwCUr3gPz9ehRDNZzMPdmXJx9EskJC6p6CZDRfxPuEHLTY7csoWl-7_uFhusQiNzuDSv"
              alt="Modern hospital exterior"
              className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-primary/90 to-transparent" />
            <div className="relative p-stack-md w-full">
              <p className="text-on-primary text-body-md mb-4 leading-relaxed">
                Immediate care facilities nearby, verified for your needs.
              </p>
              <Link
                href="/care"
                className="flex items-center justify-center gap-2 w-full bg-surface-container-lowest text-primary py-4 rounded-full text-label-md font-semibold shadow-lg hover:bg-primary-fixed transition-colors"
              >
                <span className="material-symbols-outlined" aria-hidden="true">location_on</span>
                Find Nearby Hospitals
              </Link>
            </div>
          </div>

        </div>

        {/* Disclaimer */}
        <p className="text-label-sm text-on-surface-variant text-center mt-stack-md leading-relaxed px-4">
          {profile.disclaimer}
        </p>

      </main>

      <Footer />
    </div>
  );
}

function RecommendationItem({
  icon,
  title,
  body,
  href,
}: {
  icon: string;
  title: string;
  body: string;
  href?: string;
}) {
  const inner = (
    <div className="flex items-start gap-4 p-4 rounded-xl bg-surface-container-low border border-outline-variant/30 hover:border-primary transition-colors cursor-default">
      <div className="bg-secondary-container p-2.5 rounded-full flex-shrink-0">
        <span className="material-symbols-outlined text-secondary" aria-hidden="true">{icon}</span>
      </div>
      <div>
        <h3 className="text-label-md text-on-surface font-bold mb-1">{title}</h3>
        <p className="text-body-md text-on-surface-variant">{body}</p>
      </div>
    </div>
  );
  if (href) return <Link href={href} className="block">{inner}</Link>;
  return inner;
}

function schemesForLocation(location: string): Array<{ name: string; tag: string; body: string }> {
  const loc = location.toLowerCase();
  if (loc.includes("india")) {
    return [
      { name: "Ayushman Bharat (PM-JAY)", tag: "Government · India", body: "Full coverage for cancer screenings at empanelled hospitals. Over 500 million people are eligible." },
      { name: "National Cancer Screening Programme", tag: "Free · India", body: "Free screening for oral, cervical, and breast cancers at government health centres across India." },
    ];
  }
  if (loc.includes("egypt")) {
    return [
      { name: "NHIA Coverage", tag: "Government · Egypt", body: "National Health Insurance Authority covers specialist consultations and cancer screenings." },
      { name: "Egyptian National Cancer Institute", tag: "Free · Egypt", body: "Free cancer screening and diagnostic services at NCI Cairo and affiliated centres." },
    ];
  }
  if (loc.includes("uk") || loc.includes("united kingdom") || loc.includes("england") || loc.includes("scotland") || loc.includes("wales") || loc.includes("ireland")) {
    return [
      { name: "NHS Bowel Cancer Screening", tag: "Free · UK", body: "Free screening every 2 years for adults aged 50 to 74 across England, Wales, and Scotland." },
      { name: "NHS Breast Screening Programme", tag: "Free · UK", body: "Free mammograms every 3 years for women aged 50 to 70, offered through the NHS." },
    ];
  }
  if (loc.includes("italy") || loc.includes("milan") || loc.includes("rome") || loc.includes("turin") || loc.includes("florence")) {
    return [
      { name: "Servizio Sanitario Nazionale (SSN)", tag: "Free · Italy", body: "Italy's National Health Service provides free cancer screening for colorectal, breast, and cervical cancers." },
      { name: "Piano Nazionale di Prevenzione", tag: "Government · Italy", body: "National prevention plan covers cancer screening for all residents through regional health authorities." },
    ];
  }
  if (loc.includes("usa") || loc.includes("united states") || loc.includes("canada")) {
    return [
      { name: "CDC Cancer Screening Programmes", tag: "Government · USA", body: "CDC-funded breast and cervical cancer screening for uninsured or underinsured people across all US states." },
      { name: "National Cancer Institute Resources", tag: "Free · USA / Canada", body: "NCI provides free cancer information, screening guidelines, and clinic finder for the US and Canada." },
    ];
  }
  return [
    { name: "WHO Cancer Screening Initiative", tag: "International", body: "WHO supports cancer screening access in over 150 countries with free resources and clinic referrals." },
    { name: "Union for International Cancer Control", tag: "Global Support", body: "UICC connects people with cancer screening resources and specialist referrals worldwide." },
  ];
}

function SchemeItem({ name, tag, body }: { name: string; tag: string; body: string }) {
  return (
    <div className="p-4 rounded-xl bg-secondary-container/20 border-l-4 border-secondary">
      <h4 className="text-label-md text-on-surface font-bold">{name}</h4>
      <p className="text-label-sm text-on-surface-variant mb-2">{tag}</p>
      <p className="text-body-md text-on-surface-variant">{body}</p>
    </div>
  );
}

function ConflictCard({
  conflict,
  className = "",
}: {
  conflict: RiskAssessmentConflict;
  className?: string;
}) {
  return (
    <div className={`bg-error-container border-2 border-error/30 rounded-2xl p-stack-md ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-3 h-3 rounded-full bg-error animate-pulse flex-shrink-0" />
        <p className="text-label-md font-bold text-on-error-container uppercase tracking-widest">
          I&apos;ve updated your assessment
        </p>
      </div>
      <p className="text-body-lg text-on-error-container leading-relaxed mb-4">
        Your initial profile pointed to{" "}
        <span className="font-semibold">{conflict.original_score}</span> risk.
        But your uploaded report has changed that picture. I now consider your risk to be{" "}
        <span className="font-bold">{conflict.new_score}</span>.
      </p>
      {conflict.reason && (
        <div className="bg-surface-container-lowest rounded-xl px-5 py-4 border border-error/20">
          <p className="text-label-sm text-on-surface-variant font-semibold uppercase tracking-widest mb-2">
            Why I changed this
          </p>
          <p className="text-body-md text-on-surface leading-relaxed">{conflict.reason}</p>
        </div>
      )}
    </div>
  );
}
