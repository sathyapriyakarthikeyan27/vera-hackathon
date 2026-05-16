"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSession, matchSchemes } from "@/lib/api";
import type { VERASession, RiskProfile, TimelineEvent, RiskAssessmentConflict } from "@/lib/api";

type RiskLevel = "Low" | "Moderate" | "High" | "Urgent";

const LEVEL_STYLES: Record<RiskLevel, { badge: string; bar: string; label: string }> = {
  Low: {
    badge: "bg-emerald-100 text-emerald-800",
    bar: "bg-emerald-500",
    label: "Low Risk",
  },
  Moderate: {
    badge: "bg-amber-100 text-amber-800",
    bar: "bg-amber-500",
    label: "Moderate Risk",
  },
  High: {
    badge: "bg-orange-100 text-orange-800",
    bar: "bg-orange-500",
    label: "High Risk",
  },
  Urgent: {
    badge: "bg-red-100 text-red-800",
    bar: "bg-red-500",
    label: "Urgent",
  },
};

const TIMELINE_STYLES: Record<string, { dot: string; text: string; year: string }> = {
  completed: { dot: "bg-emerald-500", text: "text-slate-700", year: "text-emerald-600" },
  missed: { dot: "bg-red-400", text: "text-red-700", year: "text-red-500" },
  urgent: {
    dot: "bg-orange-500 animate-pulse",
    text: "text-orange-700 font-semibold",
    year: "text-orange-600",
  },
};

interface ExtendedRiskProfile extends RiskProfile {
  medgemma_reasoning?: string;
}

export default function RiskPage() {
  const [session, setSession] = useState<VERASession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [schemesLoading, setSchemesLoading] = useState(false);

  useEffect(() => {
    async function load() {
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

  async function handleViewSchemes() {
    if (!session) return;
    setSchemesLoading(true);
    try {
      await matchSchemes(session.session_id);
    } finally {
      window.location.href = "/schemes";
    }
  }

  if (loading) return <LoadingState />;
  if (error || !session?.risk_profile) {
    return (
      <ErrorState
        message={error ?? "Your risk profile is not ready yet."}
      />
    );
  }

  const profile = session.risk_profile as ExtendedRiskProfile;
  const style =
    LEVEL_STYLES[profile.risk_level as RiskLevel] ?? LEVEL_STYLES.Moderate;
  const scorePercent = Math.min(100, (profile.risk_score / 15) * 100);

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-teal-900 text-white px-6 py-4 shadow-sm">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-teal-700 flex items-center justify-center font-bold text-xs">
            V
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">VERA</p>
            <p className="text-teal-300 text-xs">Risk Profile</p>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-8 space-y-5">
        {/* Risk level card */}
        <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-sm">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xs text-stone-400 uppercase tracking-widest mb-2">
                Your Risk Level
              </p>
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${style.badge}`}
              >
                {style.label}
              </span>
            </div>
            <div className="text-right">
              <p className="text-4xl font-bold text-slate-900">
                {profile.risk_score}
              </p>
              <p className="text-xs text-stone-400">out of 15</p>
            </div>
          </div>
          <div className="w-full bg-stone-100 rounded-full h-2 mb-5 overflow-hidden">
            <div
              className={`h-2 rounded-full transition-all duration-700 ${style.bar}`}
              style={{ width: `${scorePercent}%` }}
            />
          </div>
          <p className="text-sm text-slate-700 leading-relaxed">
            {profile.plain_language_summary}
          </p>
        </div>

        {/* Cancer types */}
        {profile.cancer_types_flagged.length > 0 && (
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <p className="text-xs text-stone-400 uppercase tracking-widest mb-3">
              Cancer Types to Monitor
            </p>
            <div className="flex flex-wrap gap-2">
              {profile.cancer_types_flagged.map((t) => (
                <span
                  key={t}
                  className="px-3 py-1.5 bg-teal-50 text-teal-800 rounded-full text-sm font-medium capitalize"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Screening timeline */}
        {profile.timeline.length > 0 && (
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <p className="text-xs text-stone-400 uppercase tracking-widest mb-4">
              Your Screening Timeline
            </p>
            <div className="space-y-3">
              {profile.timeline.map((event: TimelineEvent, i: number) => {
                const ts =
                  TIMELINE_STYLES[event.status] ?? TIMELINE_STYLES.missed;
                return (
                  <div key={i} className="flex items-start gap-3">
                    <div
                      className={`w-3 h-3 rounded-full flex-shrink-0 mt-0.5 ${ts.dot}`}
                    />
                    <div className="flex-1 flex items-baseline justify-between gap-2">
                      <p className={`text-sm ${ts.text}`}>{event.event}</p>
                      <span
                        className={`text-xs font-mono flex-shrink-0 ${ts.year}`}
                      >
                        {event.year}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* MedGemma reasoning */}
        {profile.medgemma_reasoning && (
          <div className="bg-teal-50 rounded-2xl border border-teal-100 p-5">
            <p className="text-xs text-teal-600 uppercase tracking-widest mb-2">
              Clinical Reasoning · MedGemma
            </p>
            <p className="text-sm text-teal-800 leading-relaxed">
              {profile.medgemma_reasoning}
            </p>
          </div>
        )}

        {/* Conflict card — shown when Agent 3 changed the assessment */}
        {session.risk_assessment?.conflict && (
          <ConflictCard conflict={session.risk_assessment.conflict} />
        )}

        {/* Disclaimer */}
        <p className="text-xs text-stone-400 text-center leading-relaxed px-4">
          {profile.disclaimer}
        </p>

        {/* Primary CTA */}
        <button
          onClick={handleViewSchemes}
          disabled={schemesLoading}
          className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-stone-300 text-white font-semibold py-4 rounded-full text-base transition-colors shadow-md"
        >
          {schemesLoading
            ? "Finding schemes near you…"
            : "Find Free Screenings Near Me →"}
        </button>

        {/* Upload records */}
        <Link
          href="/records"
          className="block w-full border-2 border-teal-200 text-teal-800 font-medium py-3.5 rounded-full text-sm transition-colors hover:bg-teal-50 text-center"
        >
          Upload a Lab Report or Scan →
        </Link>

        <Link
          href="/chat"
          className="block text-center text-sm text-stone-400 hover:text-stone-600 transition-colors"
        >
          ← Start over
        </Link>
      </div>
    </div>
  );
}

function ConflictCard({ conflict }: { conflict: RiskAssessmentConflict }) {
  return (
    <div className="bg-orange-50 border-2 border-orange-300 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
        <p className="text-xs font-bold text-orange-700 uppercase tracking-widest">
          VERA has updated your assessment
        </p>
      </div>
      <p className="text-sm text-slate-800 leading-relaxed mb-3">
        Your initial profile suggested{" "}
        <span className="font-semibold">{conflict.original_score}</span> risk,
        but your uploaded report has changed this picture. VERA now considers
        your risk{" "}
        <span className="font-semibold text-orange-700">{conflict.new_score}</span>.
      </p>
      {conflict.reason && (
        <p className="text-xs text-stone-600 leading-relaxed bg-white rounded-xl px-4 py-3 border border-orange-200">
          {conflict.reason}
        </p>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-700 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-stone-500 text-sm">Loading your risk profile…</p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center px-6">
      <div className="text-center max-w-sm">
        <p className="text-stone-600 mb-4">{message}</p>
        <Link
          href="/chat"
          className="text-teal-700 font-medium hover:underline"
        >
          Start with VERA →
        </Link>
      </div>
    </div>
  );
}
