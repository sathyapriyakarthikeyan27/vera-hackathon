"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { startRisk, answerRisk } from "@/lib/api";
import type { RiskQuestion } from "@/lib/api";

type Message = {
  id: string;
  from: "vera" | "user";
  text: string;
};

const VERA_GREETING =
  "Great — I have a few health questions to map your risk accurately. Take your time, and remember: there are no wrong answers.";

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<RiskQuestion | null>(null);
  const [textInput, setTextInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    async function init() {
      const sid = localStorage.getItem("vera_session_id");
      if (!sid) {
        router.replace("/signup");
        return;
      }
      setSessionId(sid);
      try {
        const result = await startRisk(sid);
        setCurrentQuestion(result.question);
        setMessages([
          { id: "greeting", from: "vera", text: VERA_GREETING },
          { id: "q0", from: "vera", text: result.question.question },
        ]);
      } catch {
        setMessages([
          {
            id: "err",
            from: "vera",
            text: "I had trouble connecting. Please refresh and try again.",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, [router]);

  async function handleAnswer(answer: string, label?: string) {
    if (!sessionId || !currentQuestion || isLoading) return;

    const displayText = label ?? answer;
    setMessages((prev) => [
      ...prev,
      { id: `u-${currentQuestion.id}`, from: "user", text: displayText },
    ]);
    setTextInput("");
    setIsLoading(true);
    setCurrentQuestion(null);

    try {
      const result = await answerRisk(sessionId, currentQuestion.id, answer);

      if (result.complete) {
        setMessages((prev) => [
          ...prev,
          {
            id: "complete",
            from: "vera",
            text: "Thank you for sharing that with me. I've mapped your risk profile — let me show you what I found.",
          },
        ]);
        setIsLoading(false);
        setTimeout(() => router.push("/risk"), 2200);
        return;
      }

      if (result.question) {
        setCurrentQuestion(result.question);
        setMessages((prev) => [
          ...prev,
          {
            id: `q-${result.question!.id}`,
            from: "vera",
            text: result.question!.question,
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: "err-ans",
          from: "vera",
          text: "Something went wrong. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  const isOptional = currentQuestion?.optional === true;

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      <header className="bg-teal-900 text-white px-6 py-4 flex items-center gap-3 shadow-sm flex-shrink-0">
        <div className="w-9 h-9 rounded-full bg-teal-700 flex items-center justify-center font-bold text-sm">
          V
        </div>
        <div>
          <p className="font-semibold text-sm leading-tight">VERA</p>
          <p className="text-teal-300 text-xs">Vital Early Risk Advisor</p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-xl mx-auto space-y-1">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex mb-3 ${m.from === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.from === "vera" && (
                <div className="w-7 h-7 rounded-full bg-teal-100 flex items-center justify-center text-teal-700 font-bold text-xs mr-2 flex-shrink-0 mt-1">
                  V
                </div>
              )}
              <div
                className={`max-w-xs sm:max-w-sm rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  m.from === "vera"
                    ? "bg-white border border-stone-200 text-slate-800 rounded-tl-none shadow-sm"
                    : "bg-teal-800 text-white rounded-tr-none"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start mb-3">
              <div className="w-7 h-7 rounded-full bg-teal-100 flex items-center justify-center text-teal-700 font-bold text-xs mr-2 flex-shrink-0">
                V
              </div>
              <div className="bg-white border border-stone-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm">
                <div className="flex gap-1 items-center h-4">
                  <span className="w-2 h-2 rounded-full bg-teal-300 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 rounded-full bg-teal-300 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 rounded-full bg-teal-300 animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {currentQuestion && !isLoading && (
        <div className="border-t border-stone-200 bg-white px-4 py-4 flex-shrink-0">
          <div className="max-w-xl mx-auto">
            {currentQuestion.options && currentQuestion.options.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {currentQuestion.options.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => handleAnswer(opt.value, opt.label)}
                    className="px-4 py-2 rounded-full border-2 border-teal-200 text-teal-800 text-sm font-medium hover:bg-teal-50 hover:border-teal-400 transition-colors"
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (textInput.trim()) handleAnswer(textInput.trim());
                }}
                className="space-y-2"
              >
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder={currentQuestion.placeholder || "Type your answer…"}
                    className="flex-1 rounded-full border border-stone-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent bg-stone-50"
                    autoFocus
                  />
                  <button
                    type="submit"
                    disabled={!textInput.trim()}
                    className="bg-teal-800 disabled:bg-stone-300 text-white rounded-full px-5 py-2.5 text-sm font-medium transition-colors hover:bg-teal-700 flex-shrink-0"
                  >
                    Send
                  </button>
                </div>
                {isOptional && (
                  <button
                    type="button"
                    onClick={() => handleAnswer("skip", "Nothing to add")}
                    className="w-full text-center text-xs text-stone-400 hover:text-stone-600 transition-colors py-1"
                  >
                    Skip (nothing to add)
                  </button>
                )}
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
