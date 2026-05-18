"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";

const MOCK = true; // set to false to use backend

// ── Types ────────────────────────────────────────────────────────────────────

type Message = {
  id: string;
  from: "vera" | "user";
  text: string;
  chips?: string[];
  timestamp: string;
};

// ── Mock conversation data ────────────────────────────────────────────────────

const MOCK_QA: Record<string, { text: string; chips?: string[] }> = {
  "What does this mean for me?": {
    text: "The polyp found in your colon is called a tubulovillous adenoma. Think of it as a small growth with features that can, over time, develop into cancer if left untreated.\n\nThe good news: it was caught before any cancer developed. That is exactly what screening is for. The follow-up procedure will remove the remaining part of the polyp, and regular monitoring will make sure nothing like this develops again.",
    chips: ["What is the follow-up procedure?", "How do I prepare?", "What questions should I ask?"],
  },
  "How serious is this?": {
    text: "I want to be honest with you. This finding is significant enough to act on promptly, which is why I updated your risk to High. But it is not an emergency.\n\nPolyps like this, caught early and removed, almost never develop into cancer. You are in exactly the right position. The fact that you had the screening is what matters.",
    chips: ["What happens if I wait?", "How soon should I book?"],
  },
  "What happens next?": {
    text: "Here are your next steps:\n\n1. Book an appointment with a gastroenterologist within the next 2 to 4 weeks.\n2. Bring this report and mention the partial resection.\n3. They will likely schedule a follow-up colonoscopy to remove the remaining polyp tissue.\n\nI have already found specialists near you on the Find Care page.",
    chips: ["Show me nearby specialists", "What questions should I ask?"],
  },
  "What is the follow-up procedure?": {
    text: "The follow-up is a repeat colonoscopy or completion polypectomy. The doctor removes the remaining polyp tissue using a small instrument passed through the colonoscope.\n\nIt is a day procedure under mild sedation. Most people go home the same day and feel back to normal within 24 hours.",
    chips: ["Will it hurt?", "How do I prepare?"],
  },
  "Will it hurt?": {
    text: "The procedure is done under sedation, so you will not feel any pain during it. Afterwards, some people notice mild bloating for a few hours, which passes on its own.\n\nYour doctor will give you specific guidance before the procedure.",
    chips: ["How do I prepare?"],
  },
  "How do I prepare?": {
    text: "Preparation for a colonoscopy typically includes:\n\n- A clear liquid diet the day before\n- A bowel prep drink to clear the colon\n- Stopping certain medications (your doctor will advise)\n- Arranging someone to drive you home\n\nYour gastroenterologist will give you a full preparation guide when you book.",
    chips: ["What questions should I ask?"],
  },
  "What happens if I wait?": {
    text: "The longer you wait, the more time the remaining polyp tissue has to grow. Tubulovillous adenomas have a higher chance of progressing than simpler types.\n\nI would recommend booking within 4 weeks as the report suggests. The sooner, the better.",
    chips: ["How soon should I book?", "Show me nearby specialists"],
  },
  "How soon should I book?": {
    text: "The report recommends follow-up within 4 to 6 weeks. I would aim for the earlier end of that window.\n\nOn the Find Care page, I have identified gastroenterologists near you with availability this month.",
    chips: ["Show me nearby specialists"],
  },
  "What questions should I ask?": {
    text: "Here are the key questions for your gastroenterologist:\n\n1. Was the entire polyp removed, or is additional resection needed?\n2. What type of polyp was it and what does that mean for my risk?\n3. How often should I have follow-up colonoscopies?\n4. Are there lifestyle changes that would reduce my risk?\n5. Should any family members be screened?\n\nWould you like to explore anything else?",
    chips: ["How soon should I book?", "Show me nearby specialists"],
  },
  "Show me nearby specialists": {
    text: "I have found gastroenterologists near you on the Find Care page. Apollo Hospitals Cancer Centre is 3.2 km away and has availability this month.\n\nYou can view all options including costs and whether a female doctor is available.",
    chips: [],
  },
};

const DEFAULT_RESPONSE = {
  text: "That is a good question. Based on your colonoscopy report and current risk profile, I would recommend speaking directly with your gastroenterologist about this. They will have the full clinical picture.\n\nIs there anything specific about your report findings I can help clarify?",
  chips: ["What does this mean for me?", "What happens next?", "What questions should I ask?"],
};

const INITIAL_VERA_MESSAGE: Message = {
  id: "vera-welcome",
  from: "vera",
  text: "I have reviewed your colonoscopy report. Here is what I found: a 12mm polyp in your ascending colon that was not fully removed during the procedure. The pathology describes it as a tubulovillous adenoma with low-grade dysplasia.\n\nThis does not mean you have cancer. But it does mean you need follow-up with a gastroenterologist within 4 to 6 weeks. I have already updated your risk profile to High.\n\nWhat would you like to know more about?",
  chips: ["What does this mean for me?", "How serious is this?", "What happens next?"],
  timestamp: now(),
};

function now() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Sidebar insights ─────────────────────────────────────────────────────────

const SIDEBAR_FINDINGS = [
  "12mm polyp, ascending colon",
  "Not fully resected",
  "Tubulovillous adenoma, low-grade dysplasia",
  "Follow-up within 4 to 6 weeks",
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([INITIAL_VERA_MESSAGE]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

    if (MOCK) {
      const delay = 900 + Math.random() * 600;
      await new Promise((r) => setTimeout(r, delay));
      const response = MOCK_QA[text.trim()] ?? DEFAULT_RESPONSE;
      const veraMsg: Message = {
        id: `vera-${Date.now()}`,
        from: "vera",
        text: response.text,
        chips: response.chips,
        timestamp: now(),
      };
      setMessages((prev) => [...prev, veraMsg]);
      setIsTyping(false);
      return;
    }

    // real mode: call backend
    try {
      const sid = localStorage.getItem("vera_session_id");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/companion/chat`, {
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
            <div className="p-4 bg-error-container/20 rounded-2xl border border-error/20">
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-error" style={{ fontSize: "20px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">warning</span>
                <span className="text-label-md font-bold text-error">High Risk</span>
              </div>
              <p className="text-label-sm text-on-surface-variant">Updated after colonoscopy report. Follow-up recommended within 4 to 6 weeks.</p>
            </div>

            {/* Document */}
            <div className="p-4 bg-surface-container rounded-2xl border border-outline-variant">
              <div className="flex items-center gap-2 mb-3">
                <span className="material-symbols-outlined text-primary" style={{ fontSize: "20px" }} aria-hidden="true">description</span>
                <span className="text-label-md font-bold text-on-surface">Colonoscopy Report</span>
              </div>
              <ul className="space-y-2">
                {SIDEBAR_FINDINGS.map((f, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-error flex-shrink-0 mt-2" aria-hidden="true" />
                    <span className="text-label-sm text-on-surface-variant">{f}</span>
                  </li>
                ))}
              </ul>
            </div>

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
        <section className="flex-1 flex flex-col overflow-hidden">

          {/* Disclaimer bar */}
          <div className="bg-secondary-container/20 px-6 py-2.5 flex items-center justify-center gap-2 border-b border-secondary-container/40 flex-shrink-0">
            <span className="material-symbols-outlined text-secondary" style={{ fontSize: "18px", fontVariationSettings: "'FILL' 1" }} aria-hidden="true">info</span>
            <p className="text-label-md text-on-surface-variant">
              VERA uses your uploaded records to answer questions. Always confirm with your doctor.
            </p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 md:px-10 py-8 space-y-6" style={{ scrollbarWidth: "thin", scrollbarColor: "#bfc8cd transparent" }}>

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
              <div className="flex items-start gap-3 max-w-2xl">
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
                  className="w-10 h-10 bg-primary-container hover:bg-primary disabled:bg-surface-container-high text-white rounded-full flex items-center justify-center transition-all active:scale-90 disabled:cursor-not-allowed flex-shrink-0"
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

        </section>
      </div>
    </div>
  );
}
