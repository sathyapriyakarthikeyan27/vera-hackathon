"use client";

import { useRef, useState } from "react";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { uploadRecord, reconcileRisk } from "@/lib/api";
import type { RecordsOutput, ReconcileResult } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

const MOCK = false; // set to true to use mock data

const MOCK_OUTPUT: RecordsOutput = {
  explanation: {
    document_type: "colonoscopy report",
    language: "en",
    text: "Your colonoscopy report shows an abnormal polyp in the ascending colon. The polyp is described as 12mm in size and was not fully removed during the procedure.\n\nThe pathology notes indicate features that suggest a higher-than-average risk of progression. Your gastroenterologist has recommended a follow-up resection procedure within the next 4 to 6 weeks.\n\nThis finding does not mean you have cancer. It does mean that closer monitoring and prompt follow-up is important right now.",
  },
  signals: {
    anomalies: [
      "12mm polyp in ascending colon, not fully resected",
      "Pathology: tubulovillous adenoma with low-grade dysplasia",
      "Follow-up resection recommended within 4 to 6 weeks",
    ],
    severity: "high",
    confidence: 0.91,
    specialist_signal: "Gastroenterologist",
    urgency_flag: true,
  },
  pending_reconciliation: true,
};

const MOCK_RECONCILE: ReconcileResult = {
  reconciled: true,
  conflict: true,
  original_score: "Moderate",
  new_score: "High",
  reason: "Your colonoscopy report found an abnormal polyp that was not fully removed. This is a stronger signal than your initial profile suggested. I am updating your risk to High and recommending urgent follow-up with a gastroenterologist.",
  message: "",
};

const SEVERITY_STYLES: Record<string, { badge: string; dot: string; border: string }> = {
  high: {
    badge: "bg-error-container text-on-error-container",
    dot: "bg-error",
    border: "border-error/30",
  },
  medium: {
    badge: "bg-tertiary-container/40 text-tertiary",
    dot: "bg-tertiary",
    border: "border-tertiary/30",
  },
  low: {
    badge: "bg-secondary-container text-on-secondary-container",
    dot: "bg-secondary",
    border: "border-secondary/30",
  },
};

export default function RecordsPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [output, setOutput] = useState<RecordsOutput | null>(null);
  const [reconcile, setReconcile] = useState<ReconcileResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleFile(file: File) {
    const sid = localStorage.getItem("vera_session_id");
    if (!sid) {
      setError("No session found. Please start from the beginning.");
      return;
    }

    const allowed = ["application/pdf", "image/jpeg", "image/png"];
    if (!allowed.includes(file.type)) {
      setError("Please upload a PDF, JPG, or PNG file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File too large. Maximum size is 10 MB.");
      return;
    }

    setError(null);
    setFileName(file.name);
    setUploading(true);
    setOutput(null);
    setReconcile(null);

    if (MOCK) {
      await new Promise((r) => setTimeout(r, 1800));
      setOutput(MOCK_OUTPUT);
      setUploading(false);
      setReconciling(true);
      await new Promise((r) => setTimeout(r, 1200));
      setReconcile(MOCK_RECONCILE);
      setReconciling(false);
      return;
    }

    try {
      const result = await uploadRecord(sid, file);
      setOutput(result);
      setUploading(false);

      setReconciling(true);
      const verdict = await reconcileRisk(sid);
      setReconcile(verdict);
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      setUploading(false);
      setReconciling(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  const severity = output?.signals.severity ?? "low";
  const severityStyle = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.low;

  return (
    <div className="min-h-screen bg-background">

      <Navbar />

      <main id="main-content" className="pt-32 pb-stack-lg max-w-[800px] mx-auto px-container-padding-mobile md:px-container-padding-desktop">

        {/* Hero */}
        <div className="space-y-6 mb-stack-lg">
          <h1 className="text-headline-lg md:text-headline-xl text-on-surface">
            My Records
          </h1>
          <div className="p-6 bg-primary-container/10 border border-primary-container/20 rounded-2xl flex items-start gap-4">
            <span
              className="material-symbols-outlined text-primary-container flex-shrink-0"
              style={{ fontSize: "2rem", fontVariationSettings: "'FILL' 1" }}
              aria-hidden="true"
            >
              lock
            </span>
            <p className="text-body-lg text-on-surface-variant leading-relaxed">
              Upload a lab report, MRI, or prescription. I will explain it in plain language and update your risk profile if needed. Your document is processed privately and never stored.
            </p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Upload zone */}
          {!output && (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
                dragging
                  ? "border-primary bg-primary/5"
                  : "border-outline bg-surface-container-lowest hover:border-primary hover:bg-surface-container-low"
              }`}
              role="button"
              tabIndex={0}
              aria-label="Upload medical document"
              onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={onInputChange}
                aria-hidden="true"
              />
              <div className="w-16 h-16 rounded-full bg-primary-container/10 flex items-center justify-center mx-auto mb-5">
                <span
                  className="material-symbols-outlined text-primary"
                  style={{ fontSize: "2rem" }}
                  aria-hidden="true"
                >
                  upload_file
                </span>
              </div>
              <p className="text-headline-md text-on-surface mb-2">
                Upload your medical document
              </p>
              <p className="text-body-md text-on-surface-variant mb-3">
                PDF, JPG, or PNG up to 10 MB
              </p>
              <p className="text-label-md text-on-surface-variant/60">
                Lab reports · MRI scans · Pathology · Prescriptions
              </p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-4 bg-error-container/20 border border-error/20 rounded-xl flex items-center gap-3" role="alert">
              <span className="material-symbols-outlined text-error flex-shrink-0" aria-hidden="true">error</span>
              <p className="text-body-md text-on-surface">{error}</p>
            </div>
          )}

          {/* Processing state */}
          {(uploading || reconciling) && (
            <div role="status" aria-live="polite" className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-8 text-center soft-elevation">
              <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4" aria-hidden="true" />
              <p className="text-body-md text-on-surface font-medium">
                {uploading ? "I am reading your document..." : "Updating your risk profile..."}
              </p>
              <p className="text-label-md text-on-surface-variant mt-1">
                {uploading ? fileName : "Checking for new clinical signals"}
              </p>
            </div>
          )}

          {/* Conflict card */}
          {reconcile?.conflict && (
            <div role="alert" className="bg-error-container/20 border-2 border-error/40 rounded-2xl p-6 soft-elevation">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2.5 h-2.5 rounded-full bg-error animate-pulse" aria-hidden="true" />
                <p className="text-label-md font-bold text-error uppercase tracking-widest">
                  {reconcile.uncertain ? "Findings to Review" : "Assessment Updated"}
                </p>
              </div>
              {reconcile.uncertain ? (
                <p className="text-body-lg text-on-surface leading-relaxed mb-4">
                  Your {output?.explanation.document_type ?? "document"} surfaced findings that
                  need a specialist to review. Your risk level stays{" "}
                  <span className="font-semibold">{reconcile.new_score}</span> for now, and I
                  recommend a follow-up to get a clearer picture.
                </p>
              ) : (
                <p className="text-body-lg text-on-surface leading-relaxed mb-4">
                  Your initial profile suggested{" "}
                  <span className="font-semibold">{reconcile.original_score}</span>{" "}
                  risk. Your {output?.explanation.document_type ?? "document"} has changed that picture. I now consider your risk to be{" "}
                  <span className="font-bold text-error">{reconcile.new_score}</span>.
                </p>
              )}
              {reconcile.reason && (
                <p className="text-body-md text-on-surface-variant leading-relaxed mb-5 bg-surface-container-lowest rounded-xl px-4 py-3 border border-error/20">
                  {reconcile.reason}
                </p>
              )}
              <button
                onClick={() => router.push("/risk")}
                className="w-full bg-error text-on-error font-bold py-3 rounded-xl text-label-md hover:opacity-90 transition-all active:scale-95"
              >
                View Updated Risk Profile
              </button>
            </div>
          )}

          {/* Agreement card */}
          {reconcile && !reconcile.conflict && (
            <div className="bg-secondary-container/30 border border-secondary-container rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-secondary" style={{ fontSize: "18px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">check_circle</span>
                <p className="text-label-md font-bold text-secondary uppercase tracking-widest">
                  Risk Profile Confirmed
                </p>
              </div>
              <p className="text-body-md text-on-surface-variant leading-relaxed">
                {reconcile.message}
              </p>
            </div>
          )}

          {/* Document explanation */}
          {output && (
            <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant p-6 soft-elevation">
              <div className="flex items-center justify-between mb-4">
                <p className="text-label-md text-on-surface-variant uppercase tracking-widest font-medium">
                  Document Explanation
                </p>
                <span className={`text-label-sm px-3 py-1 rounded-full font-bold ${severityStyle.badge}`}>
                  {severity.charAt(0).toUpperCase() + severity.slice(1)} severity
                </span>
              </div>
              <p className="text-body-lg text-on-surface leading-relaxed whitespace-pre-line">
                {output.explanation.text}
              </p>

              {output.signals.anomalies.length > 0 && (
                <div className={`mt-5 pt-5 border-t border-outline-variant`}>
                  <p className="text-label-md text-on-surface-variant uppercase tracking-widest mb-3 font-medium">
                    Findings extracted
                  </p>
                  <ul className="space-y-2.5">
                    {output.signals.anomalies.map((a, i) => (
                      <li key={i} className="flex items-start gap-3 text-body-md text-on-surface">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 mt-2 ${severityStyle.dot}`} aria-hidden="true" />
                        {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {output.signals.specialist_signal && (
                <div className="mt-5 bg-primary-container/10 rounded-xl px-4 py-3 border border-primary-container/20">
                  <p className="text-label-sm text-on-surface-variant mb-1 font-medium uppercase tracking-wider">
                    Specialist indicated
                  </p>
                  <p className="text-body-md text-primary font-semibold">
                    {output.signals.specialist_signal}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Chat CTA + Upload another */}
          {output && (
            <div className="flex flex-col gap-3">
              <Link
                href="/chat"
                className="w-full bg-primary text-on-primary py-4 rounded-2xl text-label-md font-bold text-center flex items-center justify-center gap-2 hover:bg-primary/90 transition-all active:scale-95"
              >
                <span className="material-symbols-outlined" style={{ fontSize: "20px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">smart_toy</span>
                Chat with VERA about this report
              </Link>
              <button
                onClick={() => {
                  setOutput(null);
                  setReconcile(null);
                  setFileName(null);
                  setError(null);
                }}
                className="w-full border-2 border-dashed border-outline rounded-2xl py-3.5 text-label-md text-on-surface-variant hover:border-primary hover:text-primary transition-colors"
              >
                + Upload another document
              </button>
            </div>
          )}

          <p className="text-label-sm text-on-surface-variant text-center leading-relaxed px-4">
            Your documents are processed in memory and never stored. VERA is a health awareness tool, not a diagnostic service. Always consult your doctor.
          </p>
        </div>

      </main>

      <Footer />

    </div>
  );
}
