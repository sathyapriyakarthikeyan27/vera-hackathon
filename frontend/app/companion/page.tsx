"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { generateFollowup } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { useRequireAuth } from "@/lib/auth";
import type { CompanionOutput, FollowUpItem } from "@/lib/api";

const LANG_LABELS: Record<string, string> = {
  en: "English",
  hi: "हिंदी",
  ta: "தமிழ்",
};

export default function CompanionPage() {
  useRequireAuth();
  const [output, setOutput] = useState<CompanionOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeLang, setActiveLang] = useState<string>("en");
  const [copied, setCopied] = useState(false);

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
    <div className="min-h-screen bg-background">
      <Navbar />

      <main
        id="main-content"
        className="pt-32 pb-stack-lg max-w-[800px] mx-auto px-container-padding-mobile md:px-0 flex flex-col gap-stack-md"
      >
        <h1 className="sr-only">Your Companion Plan</h1>

        {/* Greeting */}
        <section className="relative overflow-hidden bg-primary-container text-on-primary-container p-stack-md rounded-xl soft-elevation">
          <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none" aria-hidden="true">
            <span className="material-symbols-outlined text-9xl">guardian</span>
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-stack-sm">
              <span className="bg-on-primary-container/20 px-3 py-1 rounded-full text-label-sm uppercase tracking-wider">
                Agent 04 · Companion
              </span>
            </div>
            <p className="text-body-lg leading-relaxed opacity-90">{output.greeting}</p>
          </div>
        </section>

        {/* Escalation banner — shown when a document triggered a risk change */}
        {output.conflict_context?.triggered && (
          <section
            className="bg-error-container text-on-error-container p-stack-sm rounded-xl flex items-start gap-4 border border-error/10"
            role="alert"
          >
            <span className="material-symbols-outlined text-error flex-shrink-0" aria-hidden="true">
              warning
            </span>
            <div className="flex-1">
              <span className="text-label-md font-bold uppercase text-error">
                {output.conflict_context.uncertain ? "Findings to review" : "Risk updated"}
              </span>
              <p className="text-body-md leading-relaxed mt-0.5">
                Your{" "}
                <span className="font-bold">
                  {output.conflict_context.document_filename ||
                    output.conflict_context.document_type ||
                    "uploaded report"}
                </span>{" "}
                {output.conflict_context.uncertain ? (
                  <>
                    surfaced findings that need a specialist to review. Your risk level has not
                    changed, but your plan below helps you arrange that review.
                  </>
                ) : (
                  <>
                    changed your risk from{" "}
                    <span className="font-bold">{output.conflict_context.original_score}</span> to{" "}
                    <span className="font-bold">{output.conflict_context.new_score}</span>. Your plan
                    below reflects this updated picture.
                  </>
                )}
              </p>
            </div>
          </section>
        )}

        {/* Follow-up plan */}
        {output.follow_up_plan.length > 0 && (
          <section className="bg-surface-container-lowest p-stack-md rounded-xl soft-elevation border border-outline-variant/30">
            <h2 className="text-label-md font-bold text-on-surface-variant uppercase tracking-widest mb-stack-md">
              Your Action Plan
            </h2>
            <div className="flex flex-col gap-stack-md">
              {output.follow_up_plan.map((step: FollowUpItem, i: number) => {
                const isLast = i === output.follow_up_plan.length - 1;
                return (
                  <div key={i} className="flex gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold">
                      {i + 1}
                    </div>
                    <div
                      className={`flex-1 ${
                        isLast ? "" : "pb-stack-md border-b border-outline-variant/30"
                      }`}
                    >
                      <span className="text-label-sm text-on-surface-variant">
                        {formatDate(step.date)}
                      </span>
                      <p className="text-[18px] leading-snug font-semibold text-on-surface my-1">
                        {step.action}
                      </p>
                      <div className="flex flex-wrap gap-x-4 gap-y-2 mt-2">
                        {step.contact && (
                          <a
                            href={`tel:${step.contact}`}
                            className="text-primary font-bold flex items-center gap-1 hover:underline min-h-[44px]"
                          >
                            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                              call
                            </span>
                            {step.contact}
                          </a>
                        )}
                        {step.location && (
                          <span className="text-outline text-label-md flex items-center gap-1">
                            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                              location_on
                            </span>
                            {step.location}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Reminders now live in the notification bell (Navbar) and banner, not inline here. */}

        {/* Family message drafts */}
        {messageLangs.length > 0 && (
          <section className="bg-surface-container-lowest p-stack-md rounded-xl soft-elevation border border-outline-variant/30">
            <h2 className="text-label-md font-bold text-on-surface-variant uppercase tracking-widest mb-stack-sm">
              Message for a Loved One
            </h2>
            <p className="text-body-md text-on-surface-variant mb-stack-md">
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
                  className={`px-4 py-1.5 rounded-full text-label-md border transition-all min-h-[44px] ${
                    activeLang === lang
                      ? "bg-primary text-on-primary border-primary"
                      : "border-outline-variant text-on-surface-variant hover:bg-surface-container-high"
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
              className="bg-surface-container p-stack-md rounded-xl border border-outline-variant/20 relative"
            >
              <p className="text-body-md text-on-surface leading-relaxed pr-12">{activeMessage}</p>
              <button
                onClick={() => handleCopy(activeMessage)}
                className="absolute top-3 right-3 w-11 h-11 flex items-center justify-center rounded-lg text-primary hover:bg-surface-container-highest transition-colors"
                aria-label={copied ? "Message copied to clipboard" : "Copy message to clipboard"}
                aria-live="polite"
              >
                <span
                  className={`material-symbols-outlined ${copied ? "text-secondary" : ""}`}
                  aria-hidden="true"
                >
                  {copied ? "check" : "content_copy"}
                </span>
              </button>
            </div>
            {copied && <p className="text-label-sm text-secondary mt-2">Copied to clipboard</p>}
          </section>
        )}

        {/* Closing note */}
        <section className="bg-secondary-container/30 p-stack-md rounded-xl text-center border border-secondary/10">
          <p className="text-body-lg text-secondary italic leading-relaxed">
            VERA will be here whenever you need to revisit your plan, ask more questions, or find a
            new clinic. You are not alone in this.
          </p>
        </section>

        <div className="text-center mt-stack-sm">
          <Link
            href="/"
            className="text-outline hover:text-primary transition-colors flex items-center justify-center gap-2 text-label-md min-h-[44px]"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
              arrow_back
            </span>
            Back to home
          </Link>
        </div>
      </main>

      <Footer />
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
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div role="status" aria-live="polite" className="text-center">
        <div
          className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4"
          aria-hidden="true"
        />
        <p className="text-body-md text-on-surface-variant">Building your follow-up plan...</p>
        <p className="text-label-sm text-on-surface-variant/60 mt-2">
          Drafting messages in 3 languages
        </p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="text-center max-w-sm">
        <p className="text-body-md text-on-surface-variant mb-6">{message}</p>
        <Link href="/care" className="text-label-md text-primary font-semibold hover:underline">
          Back to Find Care
        </Link>
      </div>
    </div>
  );
}
