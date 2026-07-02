"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { useRequireAuth } from "@/lib/auth";

// ── Types ────────────────────────────────────────────────────────────────────

type Message = {
  id: string;
  from: "vera" | "user";
  text: string;
  chips?: string[];
  timestamp: string;
};

type SessionContext = {
  riskLevel: string;
  docType: string;
  docExplanation: string;
  anomalies: string[];
};

function now() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function buildWelcomeMessage(ctx: SessionContext): Message {
  let text: string;
  if (ctx.docExplanation) {
    text = `I have reviewed your ${ctx.docType}. Here is a summary of what it shows:\n\n${ctx.docExplanation}\n\nWhat would you like to know more about?`;
  } else {
    text = `Hello. I am here to help you understand your health records and risk profile. Your current risk level is ${ctx.riskLevel}. You can upload a report on the Records page, or ask me anything about your assessment.\n\nWhat would you like to know?`;
  }
  return {
    id: "vera-welcome",
    from: "vera",
    text,
    chips: ["What does this mean for me?", "What happens next?", "What questions should I ask my doctor?"],
    timestamp: now(),
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ChatPage() {
  useRequireAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sessionCtx, setSessionCtx] = useState<SessionContext>({
    riskLevel: "Unknown",
    docType: "medical document",
    docExplanation: "",
    anomalies: [],
  });
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load session context and build initial message
  useEffect(() => {
    const sid = localStorage.getItem("vera_session_id");
    if (!sid) {
      setMessages([buildWelcomeMessage({ riskLevel: "Unknown", docType: "medical document", docExplanation: "", anomalies: [] })]);
      return;
    }
    fetch(`/api/session/${sid}`)
      .then((r) => r.json())
      .then((session) => {
        const records = session.records_output || {};
        const ra = session.risk_assessment || {};
        const rp = session.risk_profile || {};
        const ctx: SessionContext = {
          riskLevel: ra.score || rp.risk_level || "Unknown",
          docType: records.document_type || "medical document",
          docExplanation: records.text || "",
          anomalies: (ra.pending_signals || []).flatMap((s: { anomalies?: string[] }) => s.anomalies || []),
        };
        setSessionCtx(ctx);
        setMessages([buildWelcomeMessage(ctx)]);
      })
      .catch(() => {
        setMessages([buildWelcomeMessage({ riskLevel: "Unknown", docType: "medical document", docExplanation: "", anomalies: [] })]);
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  async function sendMessage(text: string) {
    if (!text.trim() || isTyping) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      from: "user",
      text: text.trim(),
      timestamp: now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const sid = localStorage.getItem("vera_session_id");
      const res = await fetch("/api/companion/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid, message: text.trim() }),
      });
      const data = await res.json();
      const veraMsg: Message = {
        id: `vera-${Date.now()}`,
        from: "vera",
        text: data.reply ?? "I could not process that. Please try again.",
        timestamp: now(),
      };
      setMessages((prev) => [...prev, veraMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, from: "vera", text: "Something went wrong. Please try again.", timestamp: now() },
      ]);
    } finally {
      setIsTyping(false);
    }
  }

  function handleChip(chip: string) {
    sendMessage(chip);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">

      <Navbar />

      {/* Below navbar: sidebar + chat — fill remaining height */}
      <div className="flex flex-1 overflow-hidden pt-20">

        {/* ── Sidebar ── */}
        <aside className="hidden md:flex flex-col w-72 xl:w-80 bg-surface-container-lowest border-r border-outline-variant flex-shrink-0 overflow-y-auto">
          <div className="p-6 flex flex-col gap-6 flex-1">

            <div>
              <h2 className="text-headline-md text-primary mb-1">Session Context</h2>
              <p className="text-label-md text-on-surface-variant">Based on your most recent upload and risk profile.</p>
            </div>

            {/* Risk level */}
            <div className={`p-4 rounded-2xl border ${sessionCtx.riskLevel.toLowerCase() === "high" ? "bg-error-container/20 border-error/20" : "bg-secondary-container/20 border-secondary/20"}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`material-symbols-outlined ${sessionCtx.riskLevel.toLowerCase() === "high" ? "text-error" : "text-secondary"}`} style={{ fontSize: "20px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">
                  {sessionCtx.riskLevel.toLowerCase() === "high" ? "warning" : "info"}
                </span>
                <span className={`text-label-md font-bold ${sessionCtx.riskLevel.toLowerCase() === "high" ? "text-error" : "text-secondary"}`}>
                  {sessionCtx.riskLevel} Risk
                </span>
              </div>
              <p className="text-label-sm text-on-surface-variant">
                {sessionCtx.docExplanation ? `Based on your uploaded ${sessionCtx.docType}.` : "Based on your profile assessment."}
              </p>
            </div>

            {/* Document */}
            {sessionCtx.docExplanation ? (
              <div className="p-4 bg-surface-container rounded-2xl border border-outline-variant">
                <div className="flex items-center gap-2 mb-3">
                  <span className="material-symbols-outlined text-primary" style={{ fontSize: "20px" }} aria-hidden="true">description</span>
                  <span className="text-label-md font-bold text-on-surface capitalize">{sessionCtx.docType}</span>
                </div>
                {sessionCtx.anomalies.length > 0 ? (
                  <ul className="space-y-2">
                    {sessionCtx.anomalies.slice(0, 4).map((f, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-error flex-shrink-0 mt-2" aria-hidden="true" />
                        <span className="text-label-sm text-on-surface-variant">{f}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-label-sm text-on-surface-variant">Document uploaded. Ask me about the findings.</p>
                )}
              </div>
            ) : (
              <div className="p-4 bg-surface-container rounded-2xl border border-outline-variant">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-outline" style={{ fontSize: "20px" }} aria-hidden="true">upload_file</span>
                  <span className="text-label-md font-bold text-on-surface-variant">No document uploaded</span>
                </div>
                <p className="text-label-sm text-on-surface-variant">Upload a report on the Records page and I can answer questions about it.</p>
              </div>
            )}

            {/* Suggested questions */}
            <div>
              <p className="text-label-sm text-on-surface-variant font-medium uppercase tracking-wider mb-3">Suggested questions</p>
              <div className="flex flex-col gap-2">
                {["What does this mean for me?", "What happens next?", "Show me nearby specialists"].map((q) => (
                  <button
                    key={q}
                    onClick={() => handleChip(q)}
                    disabled={isTyping}
                    className="text-left px-4 py-3 bg-surface-container-low hover:bg-primary-container/10 border border-outline-variant hover:border-primary/30 rounded-xl text-label-md text-on-surface transition-all disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            {/* Bottom link */}
            <div className="mt-auto pt-4 border-t border-outline-variant">
              <Link href="/care" className="flex items-center gap-2 text-label-md text-primary hover:underline">
                <span className="material-symbols-outlined" style={{ fontSize: "18px" }} aria-hidden="true">local_hospital</span>
                View nearby specialists
              </Link>
            </div>
          </div>
        </aside>

        {/* ── Chat area ── */}
        <main id="main-content" className="flex-1 flex flex-col overflow-hidden">
          <h1 className="sr-only">Chat with VERA</h1>

          {/* Disclaimer bar */}
          <div className="bg-secondary-container/20 px-6 py-2.5 flex items-center justify-center gap-2 border-b border-secondary-container/40 flex-shrink-0">
            <span className="material-symbols-outlined text-secondary" style={{ fontSize: "18px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">info</span>
            <p className="text-label-md text-on-surface-variant">
              VERA uses your uploaded records to answer questions. Always confirm with your doctor.
            </p>
          </div>

          {/* Messages */}
          <div
            role="log"
            aria-live="polite"
            aria-label="Conversation with VERA"
            className="flex-1 overflow-y-auto px-4 md:px-10 py-8 space-y-6"
            style={{ scrollbarWidth: "thin", scrollbarColor: "#bfc8cd transparent" }}
          >

            {/* Welcome header */}
            <div className="flex flex-col items-center mb-6">
              <div className="w-14 h-14 bg-primary-container rounded-full flex items-center justify-center mb-3 shadow-lg shadow-primary/10">
                <span className="material-symbols-outlined text-white" style={{ fontSize: "28px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">smart_toy</span>
              </div>
              <p className="text-body-md text-on-surface-variant text-center max-w-sm">Ask me anything about your health records. I am here to help you understand what they mean.</p>
            </div>

            {messages.map((m) => (
              <div key={m.id} className={`flex items-start gap-3 max-w-2xl ${m.from === "user" ? "ml-auto flex-row-reverse" : ""}`}>

                {/* Avatar */}
                <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${m.from === "vera" ? "bg-primary-container" : "bg-secondary-container"}`}>
                  <span className="material-symbols-outlined text-white" style={{ fontSize: "18px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">
                    {m.from === "vera" ? "smart_toy" : "person"}
                  </span>
                </div>

                <div className={`flex flex-col gap-1.5 ${m.from === "user" ? "items-end" : "items-start"}`}>
                  {/* Bubble */}
                  <div className={`px-5 py-4 rounded-2xl text-body-md leading-relaxed whitespace-pre-line ${
                    m.from === "vera"
                      ? "bg-surface-container-lowest border border-outline-variant/40 text-on-surface rounded-tl-none shadow-sm"
                      : "bg-primary-container text-on-primary rounded-tr-none"
                  }`}>
                    {m.text}
                  </div>

                  {/* Chips */}
                  {m.chips && m.chips.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-1">
                      {m.chips.map((chip) => (
                        <button
                          key={chip}
                          onClick={() => handleChip(chip)}
                          disabled={isTyping}
                          className="px-4 py-1.5 bg-surface-container hover:bg-secondary-container/40 border border-outline-variant rounded-full text-label-md text-on-surface transition-colors disabled:opacity-50"
                        >
                          {chip}
                        </button>
                      ))}
                    </div>
                  )}

                  <span className="text-label-sm text-on-surface-variant/60 px-1">{m.timestamp}</span>
                </div>

              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="flex items-start gap-3 max-w-2xl" aria-label="VERA is typing">
                <div className="w-9 h-9 rounded-full bg-primary-container flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-white" style={{ fontSize: "18px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">smart_toy</span>
                </div>
                <div className="bg-surface-container-lowest border border-outline-variant/40 px-5 py-4 rounded-2xl rounded-tl-none shadow-sm">
                  <div className="flex gap-1.5 items-center h-5">
                    <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className="flex-shrink-0 px-4 md:px-10 py-5 bg-surface-container-lowest border-t border-outline-variant">
            <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
              <div className="flex items-center bg-background border border-outline rounded-full px-5 py-2 gap-3 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10 transition-all shadow-sm">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about your report..."
                  disabled={isTyping}
                  className="flex-1 bg-transparent border-none focus:outline-none focus:ring-0 text-body-md text-on-surface placeholder:text-on-surface-variant/50 disabled:opacity-50"
                  aria-label="Type your question"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isTyping}
                  className="w-11 h-11 bg-primary-container hover:bg-primary disabled:bg-surface-container-high text-white rounded-full flex items-center justify-center transition-all active:scale-90 disabled:cursor-not-allowed flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                  aria-label="Send message"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: "20px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">send</span>
                </button>
              </div>
              <p className="text-center text-label-sm text-on-surface-variant/50 mt-2">
                VERA can make mistakes. Always confirm important decisions with your doctor.
              </p>
            </form>
          </div>

        </main>
      </div>
    </div>
  );
}
