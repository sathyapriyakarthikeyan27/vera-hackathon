"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { uploadRecord, reconcileRisk } from "@/lib/api";
import type { RecordsOutput, ReconcileResult } from "@/lib/api";

const SEVERITY_STYLES = {
  high: { badge: "bg-red-100 text-red-800", dot: "bg-red-500" },
  medium: { badge: "bg-amber-100 text-amber-800", dot: "bg-amber-500" },
  low: { badge: "bg-emerald-100 text-emerald-800", dot: "bg-emerald-500" },
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

    try {
      const result = await uploadRecord(sid, file);
      setOutput(result);
      setUploading(false);

      // Immediately trigger Agent 1 reconciliation
      setReconciling(true);
      const verdict = await reconcileRisk(sid);
      setReconcile(verdict);
    } catch (e) {
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
    <div className="min-h-screen bg-stone-50">
      <header className="bg-teal-900 text-white px-6 py-4 shadow-sm">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-teal-700 flex items-center justify-center font-bold text-xs">
            V
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">VERA</p>
            <p className="text-teal-300 text-xs">Records Explainer · Agent 03</p>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-8 space-y-5">
        {/* Upload zone */}
        {!output && (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors ${
              dragging
                ? "border-teal-500 bg-teal-50"
                : "border-stone-300 bg-white hover:border-teal-400 hover:bg-stone-50"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              className="hidden"
              onChange={onInputChange}
            />
            <div className="w-12 h-12 rounded-full bg-teal-100 flex items-center justify-center mx-auto mb-4">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-teal-700"
              >
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="font-semibold text-slate-800 mb-1">
              Upload your medical document
            </p>
            <p className="text-sm text-stone-400 mb-3">
              PDF, JPG, or PNG · Max 10 MB
            </p>
            <p className="text-xs text-stone-400">
              Lab reports · MRI scans · Pathology · Prescriptions
            </p>
          </div>
        )}

        {error && (
          <p className="text-sm text-red-600 text-center">{error}</p>
        )}

        {/* Processing state */}
        {(uploading || reconciling) && (
          <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-sm text-center">
            <div className="w-10 h-10 border-4 border-teal-200 border-t-teal-700 rounded-full animate-spin mx-auto mb-3" />
            <p className="text-slate-700 font-medium text-sm">
              {uploading
                ? "VERA is reading your document…"
                : "Agent 1 is updating your risk profile…"}
            </p>
            <p className="text-stone-400 text-xs mt-1">
              {uploading ? fileName : "Reconciling new clinical signals"}
            </p>
          </div>
        )}

        {/* Conflict card — the centrepiece */}
        {reconcile?.conflict && (
          <div className="bg-orange-50 border-2 border-orange-300 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              <p className="text-xs font-bold text-orange-700 uppercase tracking-widest">
                VERA has updated your assessment
              </p>
            </div>
            <p className="text-slate-800 text-sm leading-relaxed mb-3">
              Your initial profile suggested{" "}
              <span className="font-semibold">{reconcile.original_score}</span>{" "}
              risk, but your {output?.explanation.document_type ?? "document"}{" "}
              has changed this picture. VERA now considers your risk{" "}
              <span className="font-semibold text-orange-700">
                {reconcile.new_score}
              </span>
              .
            </p>
            {reconcile.reason && (
              <p className="text-xs text-stone-600 leading-relaxed mb-4 bg-white rounded-xl px-4 py-3 border border-orange-200">
                {reconcile.reason}
              </p>
            )}
            <button
              onClick={() => router.push("/risk")}
              className="w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 rounded-full text-sm transition-colors"
            >
              View Updated Risk Profile →
            </button>
          </div>
        )}

        {/* Agreement card */}
        {reconcile && !reconcile.conflict && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <p className="text-xs font-bold text-emerald-700 uppercase tracking-widest">
                Risk profile confirmed
              </p>
            </div>
            <p className="text-sm text-emerald-800 leading-relaxed">
              {reconcile.message}
            </p>
          </div>
        )}

        {/* Document explanation */}
        {output && (
          <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-stone-400 uppercase tracking-widest">
                Document Explanation
              </p>
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-medium ${severityStyle.badge}`}
              >
                {severity.charAt(0).toUpperCase() + severity.slice(1)} severity
              </span>
            </div>
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {output.explanation.text}
            </p>

            {/* Anomalies */}
            {output.signals.anomalies.length > 0 && (
              <div className="mt-4 pt-4 border-t border-stone-100">
                <p className="text-xs text-stone-400 uppercase tracking-widest mb-2">
                  Findings extracted
                </p>
                <ul className="space-y-1.5">
                  {output.signals.anomalies.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${severityStyle.dot}`} />
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {output.signals.specialist_signal && (
              <div className="mt-4 bg-teal-50 rounded-xl px-4 py-3">
                <p className="text-xs text-teal-600 mb-0.5 font-medium">
                  Specialist indicated
                </p>
                <p className="text-sm text-teal-800 font-semibold">
                  {output.signals.specialist_signal}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Upload another */}
        {output && (
          <button
            onClick={() => {
              setOutput(null);
              setReconcile(null);
              setFileName(null);
              setError(null);
            }}
            className="w-full border-2 border-dashed border-stone-300 rounded-2xl py-4 text-sm text-stone-500 hover:border-teal-400 hover:text-teal-700 transition-colors"
          >
            + Upload another document
          </button>
        )}

        <p className="text-xs text-stone-400 text-center leading-relaxed px-4">
          Your documents are processed in memory and never stored. VERA is a
          health awareness tool — not a diagnostic service. Always consult your doctor.
        </p>

        <Link
          href="/risk"
          className="block text-center text-sm text-stone-400 hover:text-stone-600 transition-colors pb-4"
        >
          ← Back to Risk Profile
        </Link>
      </div>
    </div>
  );
}
