import Link from "next/link";

function NavPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full border border-[#1D9E75] text-[#1D9E75] text-[11px] font-medium bg-white leading-none">
      {label}
    </span>
  );
}

function FooterPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full border border-[#1D9E75] text-[#1D9E75] text-[10px] font-medium bg-white leading-none">
      {label}
    </span>
  );
}

function VeraMsg({ text }: { text: string }) {
  return (
    <div className="flex gap-2 items-end">
      <div className="w-6 h-6 rounded-full bg-[#1D9E75] flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0">
        V
      </div>
      <div
        className="bg-white border border-[#D3D1C7] px-3 py-2 text-[12px] text-[#2C2C2A] leading-relaxed max-w-[80%]"
        style={{ borderRadius: "10px 10px 10px 3px" }}
      >
        {text}
      </div>
    </div>
  );
}

function UserMsg({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div
        className="bg-[#1D9E75] text-white px-3 py-2 text-[12px] leading-relaxed max-w-[80%]"
        style={{ borderRadius: "10px 10px 3px 10px" }}
      >
        {text}
      </div>
    </div>
  );
}

const steps = [
  {
    num: "01",
    title: "We have a conversation.",
    body: "No forms, no jargon. Just a few gentle questions about you.",
  },
  {
    num: "02",
    title: "I share where you stand.",
    body: "Honest, clear, and kind. Your risk level explained in plain language.",
  },
  {
    num: "03",
    title: "I find your nearest care.",
    body: "Free clinics, the right specialist, schemes you may qualify for.",
  },
  {
    num: "04",
    title: "I stay with you.",
    body: "Checking in, reminding you, and cheering you on every step.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-white">

      {/* ── 1. NAV ─────────────────────────────────────────────────────── */}
      <nav className="bg-white border-b border-[#D3D1C7]">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className="font-semibold text-[#0F6E56]"
              style={{ fontSize: 20, letterSpacing: "-0.5px" }}
            >
              VERA
            </span>
            <span className="hidden sm:block text-[#5F5E5A] uppercase tracking-widest"
              style={{ fontSize: 10 }}>
              Vital Early Risk Advisor
            </span>
          </div>
          <div className="flex items-center gap-2">
            <NavPill label="Google Gemini" />
            <NavPill label="MedGemma" />
            <NavPill label="Vultr" />
          </div>
        </div>
      </nav>

      {/* ── 2. HERO ────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-16 lg:py-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">

          {/* Left column */}
          <div className="flex flex-col justify-center">
            <div className="flex flex-wrap gap-2 mb-8">
              <span className="inline-flex items-center px-3 py-1 rounded-full bg-[#E1F5EE] text-[#0F6E56] font-medium"
                style={{ fontSize: 11 }}>
                AI Agent Olympics
              </span>
              <span className="inline-flex items-center px-3 py-1 rounded-full bg-[#E1F5EE] text-[#0F6E56] font-medium"
                style={{ fontSize: 11 }}>
                Milan AI Week 2026
              </span>
            </div>

            <h1
              className="text-[#2C2C2A] font-medium mb-5"
              style={{ fontSize: 32, lineHeight: 1.3 }}
            >
              A little awareness today can make{" "}
              <span className="text-[#0F6E56]">all the difference</span>{" "}
              tomorrow.
            </h1>

            <p
              className="text-[#5F5E5A] mb-8"
              style={{ fontSize: 14, lineHeight: 1.8 }}
            >
              VERA is your personal health companion. She helps you understand
              your cancer risk, finds care near you, and stays by your side
              every step of the way, in your language, at your pace.
            </p>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 bg-[#1D9E75] text-white font-medium transition-opacity hover:opacity-90"
                style={{ fontSize: 14, padding: "10px 24px", borderRadius: 40 }}
              >
                Talk to VERA
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
              <p className="text-[#5F5E5A]" style={{ fontSize: 12 }}>
                Free · Private · 3 minutes · No account required
              </p>
            </div>
          </div>

          {/* Right column — chat preview */}
          <div
            className="bg-[#E1F5EE] flex flex-col gap-3"
            style={{ borderRadius: 12, padding: 20 }}
          >
            {/* Chat header */}
            <div className="flex items-center gap-3 pb-3 border-b border-[#C5E8D8]">
              <div className="w-8 h-8 rounded-full bg-[#1D9E75] flex items-center justify-center text-white font-bold flex-shrink-0"
                style={{ fontSize: 12 }}>
                V
              </div>
              <div>
                <p className="font-semibold text-[#0F6E56]" style={{ fontSize: 13 }}>VERA</p>
                <p className="text-[#5F5E5A]" style={{ fontSize: 11 }}>Online · here for you</p>
              </div>
            </div>

            {/* Chat messages */}
            <div className="flex flex-col gap-3 py-1">
              <VeraMsg text="Hi there. I'm really glad you're here. I'd love to learn a little about you so I can help. Ready?" />
              <UserMsg text="Ready." />
              <VeraMsg text="How old are you, and has anyone in your family had cancer?" />
              <UserMsg text="I'm 42. My mother had breast cancer." />
              <VeraMsg text="Thank you for sharing that with me. There's a free screening nearby that I think would be really helpful for you. Let me find it." />

              {/* Typing indicator */}
              <div className="flex gap-2 items-end">
                <div className="w-6 h-6 rounded-full bg-[#1D9E75] flex items-center justify-center text-white font-bold flex-shrink-0"
                  style={{ fontSize: 10 }}>
                  V
                </div>
                <div
                  className="bg-white border border-[#D3D1C7] px-3 py-2.5"
                  style={{ borderRadius: "10px 10px 10px 3px" }}
                >
                  <div className="flex gap-1 items-center h-3">
                    <span className="vera-dot w-1.5 h-1.5 rounded-full bg-[#1D9E75] block"
                      style={{ animationDelay: "0ms" }} />
                    <span className="vera-dot w-1.5 h-1.5 rounded-full bg-[#1D9E75] block"
                      style={{ animationDelay: "200ms" }} />
                    <span className="vera-dot w-1.5 h-1.5 rounded-full bg-[#1D9E75] block"
                      style={{ animationDelay: "400ms" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ── 3. STAT SECTION ────────────────────────────────────────────── */}
      <section className="bg-[#E1F5EE] px-6 py-8">
        <div className="max-w-5xl mx-auto">
          <p
            className="uppercase tracking-widest text-[#1D9E75] font-semibold mb-3"
            style={{ fontSize: 11 }}
          >
            The good news about early detection
          </p>
          <p
            className="font-medium text-[#085041] mb-3"
            style={{ fontSize: 48, lineHeight: 1.1 }}
          >
            99% survival at stage 1.
          </p>
          <p
            className="text-[#0F6E56] max-w-[520px]"
            style={{ fontSize: 14, lineHeight: 1.8 }}
          >
            When breast cancer is found early, survival rates are as high as
            99%. VERA is here to help you get there, with the right
            information, at the right time, in a way that feels human.
          </p>
        </div>
      </section>

      {/* ── 4. FOUR STEPS ──────────────────────────────────────────────── */}
      <section className="bg-white">
        <div className="max-w-5xl mx-auto px-6 py-16">
          <div className="grid grid-cols-1 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-[#D3D1C7]">
            {steps.map((s) => (
              <div key={s.num} className="px-6 py-6 first:pl-0 last:pr-0">
                <p
                  className="text-[#1D9E75] font-mono font-semibold mb-3"
                  style={{ fontSize: 12 }}
                >
                  {s.num}
                </p>
                <p
                  className="text-[#2C2C2A] font-medium mb-2"
                  style={{ fontSize: 13 }}
                >
                  {s.title}
                </p>
                <p
                  className="text-[#5F5E5A]"
                  style={{ fontSize: 12, lineHeight: 1.6 }}
                >
                  {s.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. DISCLAIMER ──────────────────────────────────────────────── */}
      <footer className="bg-white border-t border-[#D3D1C7]">
        <div className="max-w-5xl mx-auto px-6 py-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <p
            className="text-[#888780] max-w-md leading-relaxed"
            style={{ fontSize: 12 }}
          >
            VERA is here to inform and guide, not to diagnose. Please always
            speak with a qualified doctor. I'll help you find one.
          </p>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-[#888780]" style={{ fontSize: 11 }}>Powered by</span>
            <FooterPill label="Google Gemini" />
            <FooterPill label="MedGemma" />
            <FooterPill label="Vultr" />
          </div>
        </div>
      </footer>

    </main>
  );
}
