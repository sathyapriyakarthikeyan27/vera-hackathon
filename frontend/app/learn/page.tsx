"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { generateEducation, generateFollowup } from "@/lib/api";
import type { EducationOutput, EducationSection } from "@/lib/api";

const CANCER_EMOJI: Record<string, string> = {
  cervical: "🔬",
  breast: "🎗",
  ovarian: "🩺",
};

export default function LearnPage() {
  const [output, setOutput] = useState<EducationOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(0);
  const [companionLoading, setCompanionLoading] = useState(false);

  useEffect(() => {
    async function load() {
      const sid = localStorage.getItem("vera_session_id");
      if (!sid) {
        setError("No session found. Please start from the beginning.");
        setLoading(false);
        return;
      }
      try {
        const result = await generateEducation(sid);
        setOutput(result);
      } catch {
        setError("Could not load your education content. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleCompanion() {
    const sid = localStorage.getItem("vera_session_id");
    if (!sid) return;
    setCompanionLoading(true);
    try {
      await generateFollowup(sid);
    } finally {
      window.location.href = "/companion";
    }
  }

  if (loading) return <LoadingState />;
  if (error || !output) {
    return <ErrorState message={error ?? "Education content not available."} />;
  }

  const emoji = CANCER_EMOJI[output.cancer_type] ?? "🩺";

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-teal-900 text-white px-6 py-4 shadow-sm">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-teal-700 flex items-center justify-center font-bold text-xs">
            V
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">VERA</p>
            <p className="text-teal-300 text-xs">Education Agent</p>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-8 space-y-5">
        {/* Intro card */}
        <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">{emoji}</span>
            <div>
              <p className="text-xs text-stone-400 uppercase tracking-widest mb-0.5">
                Agent 03 · Education
              </p>
              <h1 className="text-lg font-bold text-slate-900 capitalize">
                {output.cancer_type} Cancer Screening
              </h1>
            </div>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed">
            {output.personalized_intro}
          </p>
        </div>

        {/* Sections accordion */}
        {output.sections && output.sections.length > 0 && (
          <div className="space-y-2">
            {output.sections.map((section: EducationSection, i: number) => (
              <div
                key={i}
                className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden"
              >
                <button
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-stone-50 transition-colors"
                >
                  <span className="font-semibold text-slate-800 text-sm">
                    {section.title}
                  </span>
                  <span
                    className={`text-stone-400 transition-transform duration-200 flex-shrink-0 ml-3 ${
                      expanded === i ? "rotate-180" : ""
                    }`}
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M6 9l6 6 6-6" />
                    </svg>
                  </span>
                </button>
                {expanded === i && (
                  <div className="px-5 pb-5">
                    <p className="text-sm text-slate-600 leading-relaxed">
                      {section.content}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Language indicator */}
        {output.language !== "en" && (
          <div className="bg-violet-50 rounded-xl border border-violet-100 px-4 py-3">
            <p className="text-xs text-violet-700">
              Content generated in{" "}
              {output.language === "hi"
                ? "Hindi"
                : output.language === "ta"
                ? "Tamil"
                : output.language}
            </p>
          </div>
        )}

        {/* CTA */}
        <button
          onClick={handleCompanion}
          disabled={companionLoading}
          className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-stone-300 text-white font-semibold py-4 rounded-full text-base transition-colors shadow-md"
        >
          {companionLoading
            ? "Building your follow-up plan…"
            : "Get My Follow-Up Plan →"}
        </button>

        <Link
          href="/schemes"
          className="block text-center text-sm text-stone-400 hover:text-stone-600 transition-colors pb-4"
        >
          ← Back to schemes
        </Link>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-700 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-stone-500 text-sm">
          Preparing your personalised guide…
        </p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center px-6">
      <div className="text-center max-w-sm">
        <p className="text-stone-600 mb-4">{message}</p>
        <Link href="/schemes" className="text-teal-700 font-medium hover:underline">
          ← Back to schemes
        </Link>
      </div>
    </div>
  );
}
