"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { generateFollowup, simulateCheckin } from "@/lib/api";
import type { CompanionOutput, FollowUpItem } from "@/lib/api";

const LANG_LABELS: Record<string, string> = {
  en: "English",
  hi: "हिंदी",
  ta: "தமிழ்",
};

export default function CompanionPage() {
  const [output, setOutput] = useState<CompanionOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeLang, setActiveLang] = useState<string>("en");
  const [copied, setCopied] = useState(false);
  const [checkinLoading, setCheckinLoading] = useState(false);
  const [checkinMessage, setCheckinMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const sid = localStorage.getItem("vera_session_id");
      if (!sid) {
        setError("No session found. Please start from the beginning.");
        setLoading(false);
        return;
      }
      try {
        const result = await generateFollowup(sid);
        setOutput(result);
      } catch {
        setError("Could not load your follow-up plan. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleSimulate() {
    const sid = localStorage.getItem("vera_session_id");
    if (!sid) return;
    setCheckinLoading(true);
    setCheckinMessage(null);
    try {
      const result = await simulateCheckin(sid);
      setCheckinMessage(result.checkin_message);
    } catch {
      setCheckinMessage("Hi, just checking in. It's been a few days. Have you had a chance to book your screening?");
    } finally {
      setCheckinLoading(false);
    }
  }

  async function handleCopy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard not available
    }
  }

  if (loading) return <LoadingState />;
  if (error || !output) {
    return <ErrorState message={error ?? "Follow-up plan not available."} />;
  }

  const messageLangs = Object.keys(output.family_message_drafts || {}).filter(
    (k) => k in LANG_LABELS
  );
  const activeMessage = output.family_message_drafts?.[activeLang as "en" | "hi" | "ta"] ?? "";

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-teal-900 text-white px-6 py-4 shadow-sm">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-teal-700 flex items-center justify-center font-bold text-xs" aria-hidden="true">
            V
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">VERA</p>
            <p className="text-teal-300 text-xs">Companion Agent</p>
          </div>
        </div>
      </header>

      <main id="main-content" className="max-w-2xl mx-auto px-4 py-8 space-y-5">
        <h1 className="sr-only">Your Companion Plan</h1>
        {/* Greeting */}
        <div className="bg-teal-800 text-white rounded-2xl p-6 shadow-sm">
          <p className="text-xs text-teal-300 uppercase tracking-widest mb-2">
            Agent 04 · Companion
          </p>
          <p className="text-base leading-relaxed">{output.greeting}</p>
        </div>

        {/* Follow-up plan */}
        {output.follow_up_plan.length > 0 && (
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 mb-4 uppercase tracking-wide">
              Your Action Plan
            </h2>
            <div className="space-y-4">
              {output.follow_up_plan.map((step: FollowUpItem, i: number) => (
                <div key={i} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-7 h-7 rounded-full bg-teal-100 text-teal-700 font-bold text-xs flex items-center justify-center flex-shrink-0">
                      {i + 1}
                    </div>
                    {i < output.follow_up_plan.length - 1 && (
                      <div className="w-px flex-1 bg-stone-200 mt-1.5" />
                    )}
                  </div>
                  <div className="flex-1 pb-4">
                    <p className="text-xs font-mono text-stone-400 mb-1">
                      {formatDate(step.date)}
                    </p>
                    <p className="text-sm text-slate-800 font-medium leading-snug">
                      {step.action}
                    </p>
                    {step.location && (
                      <p className="text-xs text-stone-500 mt-1">{step.location}</p>
                    )}
                    {step.contact && (
                      <a
                        href={`tel:${step.contact}`}
                        className="text-xs text-teal-700 hover:underline mt-0.5 inline-block"
                      >
                        {step.contact}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Reminder schedule */}
        {output.reminder_schedule.length > 0 && (
          <div className="bg-amber-50 rounded-2xl border border-amber-100 p-5">
            <h2 className="text-sm font-bold text-amber-900 mb-3 uppercase tracking-wide">
              Reminders
            </h2>
            <div className="space-y-3">
              {output.reminder_schedule.map((r, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0 mt-1.5" />
                  <div>
                    <p className="text-xs font-mono text-amber-700 mb-0.5">
                      {formatDate(r.date)}
                    </p>
                    <p className="text-sm text-amber-900">{r.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Family message drafts */}
        {messageLangs.length > 0 && (
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 mb-1 uppercase tracking-wide">
              Message for a Loved One
            </h2>
            <p className="text-xs text-stone-400 mb-4">
              Share this with someone you trust. A message asking for support.
            </p>

            {/* Language tabs */}
            <div className="flex gap-2 mb-4" role="tablist" aria-label="Message language">
              {messageLangs.map((lang) => (
                <button
                  key={lang}
                  onClick={() => setActiveLang(lang)}
                  role="tab"
                  aria-selected={activeLang === lang}
                  aria-controls="message-tabpanel"
                  id={`tab-${lang}`}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors min-h-[44px] min-w-[44px] ${
                    activeLang === lang
                      ? "bg-teal-800 text-white"
                      : "bg-stone-100 text-stone-600 hover:bg-stone-200"
                  }`}
                >
                  {LANG_LABELS[lang] ?? lang}
                </button>
              ))}
            </div>

            {/* Message text */}
            <div
              id="message-tabpanel"
              role="tabpanel"
              aria-labelledby={`tab-${activeLang}`}
              className="bg-stone-50 rounded-xl border border-stone-200 px-4 py-4 relative"
            >
              <p className="text-sm text-slate-700 leading-relaxed pr-10">
                {activeMessage}
              </p>
              <button
                onClick={() => handleCopy(activeMessage)}
                className="absolute top-3 right-3 text-stone-400 hover:text-teal-700 transition-colors w-11 h-11 flex items-center justify-center rounded"
                aria-label={copied ? "Message copied to clipboard" : "Copy message to clipboard"}
                aria-live="polite"
              >
                {copied ? (
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="text-emerald-500"
                  >
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                ) : (
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
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                  </svg>
                )}
              </button>
            </div>
            {copied && (
              <p className="text-xs text-emerald-600 mt-2">Copied to clipboard</p>
            )}
          </div>
        )}

        {/* Final note */}
        {/* Simulate 3 Days Later — demo button */}
        <div className="bg-teal-50 rounded-2xl border border-teal-100 p-5">
          <p className="text-sm text-teal-800 leading-relaxed text-center mb-4">
            VERA will be here whenever you need to revisit your plan, ask more
            questions, or find a new clinic. You are not alone in this.
          </p>
          <button
            onClick={handleSimulate}
            disabled={checkinLoading}
            className="w-full border-2 border-teal-300 text-teal-800 font-medium py-3 rounded-full text-sm hover:bg-teal-100 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            {checkinLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-teal-400 border-t-teal-700 rounded-full animate-spin" />
                Simulating…
              </>
            ) : (
              "⏩ Simulate 3 Days Later"
            )}
          </button>
        </div>

        {/* Check-in message card */}
        {checkinMessage && (
          <div className="bg-teal-800 text-white rounded-2xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-full bg-teal-600 flex items-center justify-center font-bold text-xs flex-shrink-0">
                V
              </div>
              <p className="text-xs text-teal-300 font-medium">
                VERA · 3 days later
              </p>
            </div>
            <p className="text-sm leading-relaxed">{checkinMessage}</p>
          </div>
        )}

        <Link
          href="/"
          className="block text-center text-sm text-stone-400 hover:text-stone-600 transition-colors pb-4"
        >
          ← Back to home
        </Link>
      </main>
    </div>
  );
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-700 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-stone-500 text-sm">Building your follow-up plan…</p>
        <p className="text-stone-400 text-xs mt-2">Drafting messages in 3 languages</p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center px-6">
      <div className="text-center max-w-sm">
        <p className="text-stone-600 mb-4">{message}</p>
        <Link href="/learn" className="text-teal-700 font-medium hover:underline">
          ← Back to education
        </Link>
      </div>
    </div>
  );
}
