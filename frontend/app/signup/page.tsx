"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signup } from "@/lib/api";
import type { Language } from "@/lib/api";

const AGE_OPTIONS = [
  { value: "under_25", label: "Under 25" },
  { value: "25_34", label: "25 – 34" },
  { value: "35_44", label: "35 – 44" },
  { value: "45_54", label: "45 – 54" },
  { value: "55_plus", label: "55 or older" },
];

const GENDER_OPTIONS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Non-binary / Prefer not to say" },
];

const LANG_OPTIONS: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिंदी (Hindi)" },
  { value: "ta", label: "தமிழ் (Tamil)" },
];

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [gender, setGender] = useState("");
  const [location, setLocation] = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValid = name.trim() && ageGroup && gender && location.trim();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await signup({
        name: name.trim(),
        age_group: ageGroup,
        gender,
        location: location.trim(),
        language,
      });
      localStorage.setItem("vera_session_id", result.session_id);
      router.push("/chat");
    } catch {
      setError("Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-teal-900 text-white px-6 py-4 shadow-sm">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-teal-700 flex items-center justify-center font-bold text-xs">
            V
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">VERA</p>
            <p className="text-teal-300 text-xs">Vital Early Risk Advisor</p>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-10">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            Let&apos;s get started
          </h1>
          <p className="text-stone-500 text-sm leading-relaxed">
            A few quick details so VERA can find you the right support.
            No account, no password — just you.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <label className="block text-sm font-semibold text-slate-800 mb-3">
              What&apos;s your name?
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your first name is fine"
              className="w-full rounded-xl border border-stone-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent bg-stone-50"
              autoFocus
              required
            />
          </div>

          {/* Age */}
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <label className="block text-sm font-semibold text-slate-800 mb-3">
              How old are you?
            </label>
            <div className="flex flex-wrap gap-2">
              {AGE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setAgeGroup(opt.value)}
                  className={`px-4 py-2 rounded-full text-sm font-medium border-2 transition-colors ${
                    ageGroup === opt.value
                      ? "bg-teal-800 text-white border-teal-800"
                      : "bg-white text-slate-700 border-stone-200 hover:border-teal-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Gender */}
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <label className="block text-sm font-semibold text-slate-800 mb-3">
              How do you identify?
            </label>
            <div className="flex flex-wrap gap-2">
              {GENDER_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setGender(opt.value)}
                  className={`px-4 py-2 rounded-full text-sm font-medium border-2 transition-colors ${
                    gender === opt.value
                      ? "bg-teal-800 text-white border-teal-800"
                      : "bg-white text-slate-700 border-stone-200 hover:border-teal-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-stone-400 mt-2">
              This helps VERA recommend the right screenings for you.
            </p>
          </div>

          {/* Location */}
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <label className="block text-sm font-semibold text-slate-800 mb-3">
              Where are you based?
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Mumbai, India or London, UK"
              className="w-full rounded-xl border border-stone-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent bg-stone-50"
              required
            />
            <p className="text-xs text-stone-400 mt-2">
              Used only to find free clinics and schemes near you.
            </p>
          </div>

          {/* Language */}
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <label className="block text-sm font-semibold text-slate-800 mb-3">
              Which language would you prefer?
            </label>
            <div className="flex gap-2">
              {LANG_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setLanguage(opt.value)}
                  className={`flex-1 py-2.5 rounded-full text-sm font-medium border-2 transition-colors ${
                    language === opt.value
                      ? "bg-teal-800 text-white border-teal-800"
                      : "bg-white text-slate-700 border-stone-200 hover:border-teal-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600 text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={!isValid || loading}
            className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-stone-300 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-full text-base transition-colors shadow-md flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Setting up VERA…
              </>
            ) : (
              "Start my health check →"
            )}
          </button>

          <p className="text-xs text-stone-400 text-center leading-relaxed">
            No account needed. Your data is private and session-only.
            VERA is a health awareness tool — not a diagnostic service.
          </p>
        </form>
      </div>
    </div>
  );
}
