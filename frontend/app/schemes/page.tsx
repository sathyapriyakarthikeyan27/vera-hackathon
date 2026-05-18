"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { matchSchemes } from "@/lib/api";
import type { SchemesOutput, SchemeMatch, Clinic } from "@/lib/api";

interface ExtendedSchemeMatch extends SchemeMatch {
  why_matches?: string;
}

export default function SchemesPage() {
  const router = useRouter();
  const [output, setOutput] = useState<SchemesOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const sid = localStorage.getItem("vera_session_id");
      if (!sid) {
        localStorage.removeItem("vera_session_id");
        router.replace("/signup");
        return;
      }
      try {
        const result = await matchSchemes(sid);
        setOutput(result);
      } catch {
        setError("Could not load schemes. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  if (loading) return <LoadingState />;
  if (error || !output) {
    return <ErrorState message={error ?? "No scheme data available."} />;
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-teal-900 text-white px-6 py-4 shadow-sm">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-teal-700 flex items-center justify-center font-bold text-xs">
            V
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">VERA</p>
            <p className="text-teal-300 text-xs">Scheme Navigator</p>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
        {output.matched_schemes.length > 0 && (
          <section>
            <h2 className="text-lg font-bold text-slate-900 mb-1">
              Government Schemes for You
            </h2>
            <p className="text-sm text-stone-500 mb-4">
              Free and subsidised cancer screening programmes available in your area.
            </p>
            <div className="space-y-4">
              {output.matched_schemes.map((s, i) => (
                <SchemeCard key={i} scheme={s as ExtendedSchemeMatch} />
              ))}
            </div>
          </section>
        )}

        {output.nearest_clinics.length > 0 && (
          <section>
            <h2 className="text-lg font-bold text-slate-900 mb-1">
              Free Screening Near You
            </h2>
            <p className="text-sm text-stone-500 mb-4">
              Reputable government hospitals offering free cancer screening.
            </p>
            <div className="space-y-4">
              {output.nearest_clinics.map((c, i) => (
                <ClinicCard key={i} clinic={c} />
              ))}
            </div>
          </section>
        )}

        <p className="text-xs text-stone-400 text-center leading-relaxed px-4">
          VERA provides health navigation only. Always verify scheme eligibility
          directly with the provider. Consult a qualified doctor before making
          health decisions.
        </p>

        <Link
          href="/learn"
          className="block w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold py-4 rounded-full text-base transition-colors shadow-md text-center"
        >
          Learn About Your Screening →
        </Link>

        <Link
          href="/"
          className="block text-center text-sm text-stone-400 hover:text-stone-600 transition-colors pb-4"
        >
          ← Back to home
        </Link>
      </div>
    </div>
  );
}

function SchemeCard({ scheme }: { scheme: ExtendedSchemeMatch }) {
  return (
    <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4 mb-2">
        <h3 className="font-semibold text-slate-900 text-sm leading-snug">
          {scheme.scheme_name}
        </h3>
        <span className="flex-shrink-0 text-xs bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full font-medium">
          Free
        </span>
      </div>
      <p className="text-sm text-slate-600 leading-relaxed mb-3">
        {scheme.description}
      </p>
      <div className="space-y-1 mb-3">
        <p className="text-xs text-stone-500">
          <span className="font-medium text-stone-700">Eligible: </span>
          {scheme.eligibility_summary}
        </p>
        <p className="text-xs text-stone-500">
          <span className="font-medium text-stone-700">Covers: </span>
          {scheme.coverage}
        </p>
      </div>
      {scheme.why_matches && (
        <p className="text-xs text-teal-700 bg-teal-50 rounded-xl px-3 py-2 leading-relaxed mb-3">
          {scheme.why_matches}
        </p>
      )}
      {scheme.url && (
        <a
          href={scheme.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-teal-700 hover:underline font-medium"
        >
          Learn more →
        </a>
      )}
    </div>
  );
}

function ClinicCard({ clinic }: { clinic: Clinic }) {
  return (
    <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="font-semibold text-slate-900 text-sm leading-snug">
          {clinic.name}
        </h3>
        <span
          className={`flex-shrink-0 text-xs px-2.5 py-1 rounded-full font-medium ${
            clinic.cost === "Free"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-amber-100 text-amber-700"
          }`}
        >
          {clinic.cost}
        </span>
      </div>
      <p className="text-xs text-stone-500 mb-3">{clinic.address}</p>
      {clinic.services.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {clinic.services.map((s) => (
            <span
              key={s}
              className="text-xs bg-stone-100 text-stone-600 px-2.5 py-1 rounded-full"
            >
              {s}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center flex-wrap gap-4 text-xs">
        {clinic.female_doctor_available && (
          <span className="text-teal-700 font-medium">
            Female doctor available
          </span>
        )}
        {clinic.contact && (
          <a
            href={`tel:${clinic.contact}`}
            className="text-teal-700 hover:underline"
          >
            {clinic.contact}
          </a>
        )}
      </div>
      {clinic.appointment_url && (
        <a
          href={clinic.appointment_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-block text-xs text-white bg-teal-800 hover:bg-teal-700 px-4 py-2 rounded-full font-medium transition-colors"
        >
          Book Appointment →
        </a>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-700 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-stone-500 text-sm">
          Finding schemes and clinics near you…
        </p>
        <p className="text-stone-400 text-xs mt-2">This may take a moment</p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center px-6">
      <div className="text-center max-w-sm">
        <p className="text-stone-600 mb-4">{message}</p>
        <Link href="/risk" className="text-teal-700 font-medium hover:underline">
          ← Back to Risk Profile
        </Link>
      </div>
    </div>
  );
}
