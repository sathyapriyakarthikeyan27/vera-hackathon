"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { startRisk, answerRisk } from "@/lib/api";
import type { RiskQuestion } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

const MOCK = true; // set to false to use backend

const TOTAL_STEPS = 6;

const MOCK_QUESTIONS: import("@/lib/api").RiskQuestion[] = [
  { id: "q1", question: "Does anyone in your immediate family have a history of cancer?", type: "choice", key: "family_history", options: [{ value: "yes", label: "Yes" }, { value: "no", label: "No" }, { value: "unsure", label: "Not sure" }], why_we_ask: "Family history is one of the strongest predictors of cancer risk." },
  { id: "q2", question: "Do you currently smoke or use tobacco products?", type: "choice", key: "smoking", options: [{ value: "never", label: "Never" }, { value: "former", label: "Former smoker" }, { value: "current", label: "Current smoker" }], why_we_ask: "Smoking significantly raises risk for lung, throat, and bladder cancers." },
  { id: "q3", question: "When did you last have a cancer screening?", type: "choice", key: "last_screening", options: [{ value: "within_1yr", label: "Within the last year" }, { value: "1_3yr", label: "1 to 3 years ago" }, { value: "over_5yr", label: "More than 5 years ago" }, { value: "never", label: "Never" }], why_we_ask: "Regular screenings catch cancer early, when it is most treatable." },
  { id: "q4", question: "How would you describe your alcohol consumption?", type: "choice", key: "alcohol", options: [{ value: "none", label: "None" }, { value: "occasional", label: "Occasional (1-2 drinks a week)" }, { value: "moderate", label: "Moderate (3-7 drinks a week)" }, { value: "heavy", label: "Heavy (more than 7 drinks a week)" }], why_we_ask: "Regular alcohol use is linked to increased risk for several cancers." },
  { id: "q5", question: "Do you have any existing medical conditions you manage regularly?", type: "choice", key: "conditions", options: [{ value: "none", label: "No" }, { value: "diabetes", label: "Diabetes" }, { value: "hypertension", label: "High blood pressure" }, { value: "other", label: "Other chronic condition" }], why_we_ask: "Some conditions affect cancer screening recommendations." },
  { id: "q6", question: "Is there anything health-related that has been on your mind lately?", type: "text", key: "symptoms", optional: true, placeholder: "Share any symptoms or concerns, or skip if nothing comes to mind.", why_we_ask: "Even vague concerns can be relevant. VERA will never alarm you unnecessarily." },
];


export default function AssessmentPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [question, setQuestion] = useState<RiskQuestion | null>(null);
  const [selectedValue, setSelectedValue] = useState<string | null>(null);
  const [textAnswer, setTextAnswer] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      const sid = localStorage.getItem("vera_session_id");
      if (!sid) { router.replace("/signup"); return; }
      setSessionId(sid);
      if (MOCK) {
        setQuestion(MOCK_QUESTIONS[0]);
        setIsLoading(false);
        return;
      }
      try {
        const result = await startRisk(sid);
        setQuestion(result.question);
      } catch {
        setError("Could not start the assessment. Please refresh and try again.");
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, [router]);

  async function handleAnswer(answer: string) {
    if (!question || isSubmitting) return;
    setIsSubmitting(true);
    setSelectedValue(answer);

    if (MOCK) {
      await new Promise((r) => setTimeout(r, 400));
      const nextIndex = currentStep; // currentStep is 1-based, MOCK_QUESTIONS is 0-based
      if (nextIndex >= MOCK_QUESTIONS.length) {
        localStorage.setItem("vera_assessment_complete", "1");
        router.push("/risk");
        return;
      }
      setCurrentStep((s) => s + 1);
      setQuestion(MOCK_QUESTIONS[nextIndex]);
      setSelectedValue(null);
      setTextAnswer("");
      setIsSubmitting(false);
      return;
    }

    if (!sessionId) return;
    try {
      const result = await answerRisk(sessionId, question.id, answer, question.key);
      if (result.complete) {
        localStorage.setItem("vera_assessment_complete", "1");
        router.push("/risk");
        return;
      }
      if (result.question) {
        setCurrentStep((s) => s + 1);
        setQuestion(result.question);
        setSelectedValue(null);
        setTextAnswer("");
      }
    } catch {
      setError("Something went wrong. Please try again.");
      setSelectedValue(null);
    } finally {
      setIsSubmitting(false);
    }
  }

  const progressPercent = Math.round(((currentStep - 1) / TOTAL_STEPS) * 100);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <p className="text-body-md text-on-surface-variant">Preparing your assessment...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6">
        <div className="text-center max-w-sm">
          <p className="text-body-md text-on-surface-variant mb-6">{error}</p>
          <Link href="/signup" className="text-label-md text-primary font-semibold hover:underline">
            Start over
          </Link>
        </div>
      </div>
    );
  }

  if (!question) return null;

  return (
    <div className="min-h-screen bg-background">
      <Navbar right={
        <div className="bg-primary text-on-primary text-label-md px-5 py-2 rounded-full">
          {currentStep} of {TOTAL_STEPS}
        </div>
      } />

      <main className="pt-24 pb-stack-lg min-h-screen">

        {/* Progress bar */}
        <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop mt-stack-md">
          <div className="flex items-center justify-between mb-4">
            <span className="text-label-md text-primary font-bold">Step {currentStep} of {TOTAL_STEPS}</span>
            <span className="text-label-md text-on-surface-variant">{progressPercent}% Complete</span>
          </div>
          <div className="w-full h-3 bg-surface-container-highest rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-container rounded-full transition-all duration-500"
              style={{ width: `${Math.max(progressPercent, 4)}%`, boxShadow: "0 0 12px rgba(45, 125, 154, 0.3)" }}
            />
          </div>
        </div>

        {/* Question section */}
        <section className="max-w-[800px] mx-auto px-container-padding-mobile md:px-container-padding-desktop mt-stack-lg">

          <div className="mb-8">
            <h1 className="text-headline-lg-mobile md:text-headline-lg text-on-surface mb-3">
              {question.question}
            </h1>
            {question.optional && (
              <p className="text-body-lg text-on-surface-variant">
                This is optional. Share anything that has been on your mind, or skip.
              </p>
            )}
          </div>

          {/* Choice options */}
          {question.type === "choice" && question.options && question.options.length > 0 && (
            <div className="grid grid-cols-1 gap-4">
              {question.options.map((opt) => {
                const isSelected = selectedValue === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => handleAnswer(opt.value)}
                    disabled={isSubmitting}
                    className={`group flex items-center p-6 bg-surface-container-lowest border rounded-xl text-left transition-all duration-200 disabled:cursor-not-allowed ${
                      isSelected
                        ? "border-primary bg-primary-fixed/20"
                        : "border-outline-variant hover:border-primary hover:bg-surface-container-low"
                    }`}
                  >
                    <div className="w-11 h-11 flex-shrink-0 flex items-center justify-center rounded-full bg-secondary-container text-on-secondary-container mr-5 group-hover:scale-110 transition-transform">
                      <span className="material-symbols-outlined text-xl" aria-hidden="true">
                        {isSelected ? "check_circle" : "radio_button_unchecked"}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="text-headline-md text-on-surface">{opt.label}</p>
                    </div>
                    <div className={`ml-4 transition-opacity ${isSelected ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                      {isSubmitting && isSelected ? (
                        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                      ) : (
                        <span className="material-symbols-outlined text-primary" aria-hidden="true">check_circle</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Text input */}
          {question.type === "text" && (
            <form
              onSubmit={(e) => { e.preventDefault(); handleAnswer(textAnswer.trim() || "skip"); }}
              className="space-y-4"
            >
              <textarea
                value={textAnswer}
                onChange={(e) => setTextAnswer(e.target.value)}
                placeholder={question.placeholder || "Share any symptoms or health concerns..."}
                rows={4}
                className="w-full rounded-xl border border-outline bg-surface-container-low px-4 py-3 text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 resize-none transition-all"
                autoFocus
              />
              <div className="flex items-center gap-4">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-primary text-on-primary text-label-md px-10 py-4 rounded-full shadow-md hover:bg-primary/90 transition-all active:scale-95 flex items-center gap-2 disabled:opacity-60"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
                      Finishing up...
                    </>
                  ) : (
                    <>
                      Continue
                      <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
                    </>
                  )}
                </button>
                {question.optional && (
                  <button
                    type="button"
                    onClick={() => handleAnswer("skip")}
                    disabled={isSubmitting}
                    className="text-label-md text-on-surface-variant hover:text-primary transition-colors px-6 py-4 rounded-full hover:bg-surface-container-high disabled:opacity-60"
                  >
                    Skip
                  </button>
                )}
              </div>
            </form>
          )}

          {/* Start over link */}
          {question.type === "choice" && (
            <div className="flex items-center justify-between mt-stack-lg">
              <Link
                href="/signup"
                className="flex items-center gap-2 px-6 py-3 rounded-full text-label-md text-on-surface-variant hover:bg-surface-container-high transition-all"
              >
                <span className="material-symbols-outlined" aria-hidden="true">arrow_back</span>
                Start Over
              </Link>
            </div>
          )}

          {/* Why we ask context card */}
          {question.why_we_ask && (
            <div className="mt-stack-lg p-6 bg-secondary-container/30 rounded-2xl flex gap-4 items-start border border-secondary-container">
              <span
                className="material-symbols-outlined text-secondary flex-shrink-0"
                style={{ fontSize: "2rem", fontVariationSettings: "'FILL' 1" }}
                aria-hidden="true"
              >
                info
              </span>
              <div>
                <p className="text-body-md text-on-secondary-container font-medium mb-1">Why we ask this</p>
                <p className="text-label-md text-on-secondary-container/80 leading-relaxed">{question.why_we_ask}</p>
              </div>
            </div>
          )}
        </section>

        {/* Decorative image */}
        <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop mt-stack-lg opacity-30">
          <img
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuCwqo1_IdrBINEIKKlRUW_VGhhJiPsiesDPMctkNummzL6nOnw28zf3zA9JQF1ufGwy26eECITw6e0MobxOyKFuZzUhe1SWYVwh1fqwH9Cl7Ydz9v-mgnwW3ItgVZKnsUuGPNnrPfQ_aV7MriprJ9JSqL7YsOttyaxKrAkrDcY3pqFDl1SoF2LgnZobyIfBGbtkGK8viCTmR2oAvFPsaH4xnZx2YMSl19-qMHRqiBCZBMPfBCy6vSNwjhJBooh2Ia_-QM9eFUrOwVYa"
            alt=""
            aria-hidden="true"
            className="w-full h-48 object-cover rounded-3xl mix-blend-multiply"
          />
        </div>
      </main>

      <Footer />
    </div>
  );
}
