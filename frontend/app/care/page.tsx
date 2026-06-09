"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { matchSchemes } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import type { SchemesOutput, Clinic, SchemeMatch } from "@/lib/api";

const MOCK = false; // set to true to use mock data

const MOCK_CLINICS: Clinic[] = [
  {
    name: "Apollo Hospitals Cancer Centre",
    distance_km: 3.2,
    address: "21 Greams Road, Chennai, Tamil Nadu 600006",
    female_doctor_available: true,
    cost: "Free",
    next_available: "2026-05-22",
    contact: "+91 44 2829 0200",
    appointment_url: null,
    services: ["Colorectal Screening", "Colonoscopy", "Oncology Consultation"],
  },
  {
    name: "AIIMS Cancer Institute",
    distance_km: 5.8,
    address: "Sri Aurobindo Marg, New Delhi 110029",
    female_doctor_available: false,
    cost: "Free",
    next_available: "2026-05-25",
    contact: "+91 11 2658 8500",
    appointment_url: null,
    services: ["General Oncology", "Lung Screening", "Blood Cancer Detection"],
  },
  {
    name: "Tata Memorial Hospital",
    distance_km: 8.1,
    address: "Dr E Borges Road, Parel, Mumbai 400012",
    female_doctor_available: true,
    cost: "Subsidized",
    next_available: "2026-05-28",
    contact: "+91 22 2417 7000",
    appointment_url: null,
    services: ["Cancer Surgery", "Chemotherapy", "Radiation Oncology"],
  },
  {
    name: "Regional Cancer Centre",
    distance_km: 12.4,
    address: "Medical College PO, Thiruvananthapuram, Kerala 695011",
    female_doctor_available: true,
    cost: "Free",
    next_available: null,
    contact: "+91 471 244 2541",
    appointment_url: null,
    services: ["Gynaecologic Oncology", "Breast Cancer Screening", "Palliative Care"],
  },
];


export default function CarePage() {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [schemes, setSchemes] = useState<SchemeMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (MOCK) {
        setClinics(MOCK_CLINICS);
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
        const result: SchemesOutput = await matchSchemes(sid);
        setClinics(result.nearest_clinics);
        setSchemes(result.matched_schemes ?? []);
      } catch {
        setError("Could not load care recommendations. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div role="status" aria-live="polite" className="text-center">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" aria-hidden="true" />
          <p className="text-body-md text-on-surface-variant">Finding clinics and hospitals near you...</p>
          <p className="text-label-md text-on-surface-variant/60 mt-2">This may take a moment</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6">
        <div className="text-center max-w-sm">
          <p className="text-body-md text-on-surface-variant mb-6">{error}</p>
          <Link href="/risk" className="text-label-md text-primary font-semibold hover:underline">
            Back to Risk Profile
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">

      <Navbar />

      <main id="main-content" className="pt-32 pb-stack-lg max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop">

        {/* Hero */}
        <div className="space-y-6 mb-stack-lg">
          <h1 className="text-headline-lg md:text-headline-xl text-on-surface">
            Care Recommendations
          </h1>
          <div className="p-6 bg-primary-container/10 border border-primary-container/20 rounded-2xl flex items-start gap-4">
            <span
              className="material-symbols-outlined text-primary-container flex-shrink-0"
              style={{ fontSize: "2rem", fontVariationSettings: "'FILL' 1" }}
              aria-hidden="true"
            >
              info
            </span>
            <p className="text-body-lg text-on-surface-variant leading-relaxed">
              Based on your <span className="font-bold text-primary">VERA Assessment</span>, I&apos;ve found hospitals and screening clinics near you. All facilities listed offer cancer screening services relevant to your risk profile.
            </p>
          </div>
        </div>

        {/* Matched schemes */}
        {schemes.length > 0 && (
          <div className="mb-stack-lg">
            <h2 className="text-headline-md text-on-surface mb-4">Government Schemes for You</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {schemes.map((s, i) => (
                <div key={i} className="bg-surface-container-lowest p-5 rounded-2xl border-l-4 border-secondary soft-elevation">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h3 className="text-label-md font-bold text-on-surface">{s.scheme_name}</h3>
                    {s.url && (
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-label-sm text-primary hover:underline flex-shrink-0"
                        aria-label={`Learn more about ${s.scheme_name}`}
                      >
                        Learn more
                      </a>
                    )}
                  </div>
                  <p className="text-body-md text-on-surface-variant mb-2">{s.description}</p>
                  <p className="text-label-sm text-secondary font-medium">{s.eligibility_summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Clinics grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-stack-lg">
          {clinics.map((clinic, i) => (
            <ClinicCard key={i} clinic={clinic} isTopMatch={i === 0} />
          ))}

          {/* Retake CTA */}
          <article className="bg-primary-container text-on-primary-container p-6 rounded-2xl soft-elevation flex flex-col justify-center items-center text-center space-y-6">
            <div className="w-16 h-16 bg-on-primary-container/10 rounded-full flex items-center justify-center">
              <span className="material-symbols-outlined text-4xl" aria-hidden="true">question_mark</span>
            </div>
            <div className="space-y-2">
              <h2 className="text-headline-md">Not what you expected?</h2>
              <p className="text-body-md leading-relaxed">
                You can retake your assessment any time if your symptoms or health goals have changed.
              </p>
            </div>
            <Link
              href="/assessment"
              className="w-full bg-on-primary-container text-primary-container py-3 rounded-xl text-label-md font-bold hover:opacity-90 transition-all text-center"
            >
              Retake Assessment
            </Link>
          </article>
        </div>

        {/* FAQ section */}
        <section className="bg-surface-container-low p-8 rounded-3xl border border-outline-variant">
          <div className="max-w-3xl mb-8">
            <h2 className="text-headline-lg text-on-surface mb-4">
              What to Expect at Your Screening
            </h2>
            <p className="text-body-lg text-on-surface-variant">
              It is natural to have questions before booking. I am here to help you feel confident and prepared.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FAQItem
              icon="help_center"
              title="What happens at a screening?"
              body="Think of it as a detailed health check-in. The specialist will review your history, perform non-invasive tests, and discuss any concerns in a supportive environment."
            />
            <FAQItem
              icon="event_note"
              title="How should I prepare?"
              body="Usually no special preparation is needed. Bring a list of any medications you take and your VERA assessment summary to help guide the conversation."
            />
            <FAQItem
              icon="verified"
              title="Is early detection effective?"
              body="Absolutely. Finding trends early gives you the best chance to manage your health proactively, often with simple lifestyle changes rather than complex treatment."
            />
          </div>
        </section>

        {/* Companion CTA */}
        <div className="mt-stack-lg bg-teal-800 text-white rounded-3xl p-8 flex flex-col md:flex-row items-center gap-6">
          <div className="flex-shrink-0 w-14 h-14 rounded-full bg-teal-600 flex items-center justify-center">
            <span className="material-symbols-outlined text-3xl" aria-hidden="true">calendar_month</span>
          </div>
          <div className="flex-1 text-center md:text-left">
            <h2 className="text-headline-md mb-1">Your follow-up plan is ready</h2>
            <p className="text-body-md text-teal-200 leading-relaxed">
              VERA has prepared a personalised action plan with reminders, next steps, and a message you can share with someone you trust.
            </p>
          </div>
          <Link
            href="/companion"
            className="flex-shrink-0 bg-white text-teal-900 font-bold px-6 py-3 rounded-xl text-label-md hover:bg-teal-50 transition-colors min-w-[180px] text-center"
            aria-label="View your companion follow-up plan"
          >
            View my plan
          </Link>
        </div>

        {/* Disclaimer */}
        <p className="text-label-sm text-on-surface-variant text-center mt-stack-md leading-relaxed px-4">
          VERA provides health navigation only. Always verify availability directly with the facility. Consult a qualified doctor before making health decisions.
        </p>

      </main>

      <Footer />
    </div>
  );
}

function ClinicCard({ clinic, isTopMatch }: { clinic: Clinic; isTopMatch: boolean }) {
  return (
    <article className={`bg-surface-container-lowest p-6 rounded-2xl soft-elevation flex flex-col space-y-5 transition-all ${isTopMatch ? "border-2 border-primary" : "border border-outline-variant hover:border-primary/50"}`}>
      <div className="flex justify-between items-start gap-3">
        <div>
          <span className={`px-3 py-1 rounded-full text-label-sm font-bold uppercase tracking-wider ${clinic.cost === "Free" ? "bg-secondary-container text-on-secondary-container" : "bg-surface-container-high text-on-surface-variant"}`}>
            {clinic.cost} · {clinic.distance_km} km away
          </span>
          <h2 className="text-headline-md text-on-surface mt-3">{clinic.name}</h2>
        </div>
        {isTopMatch && (
          <div className="flex items-center gap-1 bg-secondary-container px-2 py-1 rounded-lg flex-shrink-0">
            <span
              className="material-symbols-outlined text-on-secondary-container"
              style={{ fontSize: "18px", fontVariationSettings: "'FILL' 1" }}
              aria-hidden="true"
            >
              verified
            </span>
            <span className="text-label-sm text-on-secondary-container">Nearest</span>
          </div>
        )}
      </div>

      <div className={`p-4 bg-surface-container-low rounded-xl border-l-4 ${isTopMatch ? "border-primary" : "border-outline"}`}>
        <p className={`text-label-sm font-bold uppercase mb-1 ${isTopMatch ? "text-primary" : "text-on-surface-variant"}`}>
          Location
        </p>
        <p className="text-body-md text-on-surface-variant">{clinic.address}</p>
      </div>

      <div className="flex-grow space-y-3">
        {clinic.services.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {clinic.services.map((s) => (
              <span key={s} className="text-label-sm bg-surface-container text-on-surface-variant px-3 py-1 rounded-full">
                {s}
              </span>
            ))}
          </div>
        )}
        {clinic.female_doctor_available && (
          <p className="text-label-md text-secondary font-semibold flex items-center gap-1">
            <span className="material-symbols-outlined text-base" aria-hidden="true">person</span>
            Female doctor available
          </p>
        )}
        {clinic.next_available && (
          <p className="text-label-md text-on-surface-variant">
            <span className="font-semibold text-on-surface">Next available: </span>{clinic.next_available}
          </p>
        )}
      </div>

      <div className="flex gap-3 pt-4 border-t border-outline-variant">
        {clinic.appointment_url ? (
          <a
            href={clinic.appointment_url}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex-grow py-2.5 rounded-xl text-label-md font-bold text-center transition-colors ${isTopMatch ? "bg-primary text-on-primary hover:bg-primary/90" : "border border-primary text-primary hover:bg-primary/5"}`}
          >
            Book Appointment
          </a>
        ) : (
          <span className={`flex-grow py-2.5 rounded-xl text-label-md font-bold text-center ${isTopMatch ? "bg-primary text-on-primary" : "border border-primary text-primary"}`}>
            Walk In Welcome
          </span>
        )}
        {clinic.contact && (
          <a
            href={`tel:${clinic.contact}`}
            className="min-h-[44px] min-w-[44px] px-4 py-2.5 border border-primary text-primary rounded-xl flex items-center justify-center hover:bg-primary/5 transition-colors"
            aria-label={`Call ${clinic.name}`}
          >
            <span className="material-symbols-outlined" aria-hidden="true">call</span>
          </a>
        )}
      </div>
    </article>
  );
}

function FAQItem({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-primary" aria-hidden="true">{icon}</span>
        <h3 className="text-body-md font-bold text-on-surface">{title}</h3>
      </div>
      <p className="text-body-md text-on-surface-variant leading-relaxed">{body}</p>
    </div>
  );
}
