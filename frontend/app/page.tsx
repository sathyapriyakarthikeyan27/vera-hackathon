import Link from "next/link";
import { StartAssessmentButton } from "@/components/StartAssessmentButton";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <div className="bg-background text-on-surface text-body-md selection:bg-primary-fixed-dim">

      <Navbar right={
        <StartAssessmentButton className="bg-primary text-on-primary text-label-md px-6 py-3 rounded-full hover:bg-primary/90 active:scale-95 transition-all">
          Start Assessment
        </StartAssessmentButton>
      } />

      <main className="pt-20">

        {/* ── Hero Section ─────────────────────────────────────────── */}
        <section className="relative overflow-hidden py-stack-lg md:py-32">
          <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop grid md:grid-cols-2 gap-gutter items-center">

            {/* Left column */}
            <div className="z-10">
              <h1 className="text-headline-xl text-primary mb-6 leading-tight">
                Early Detection is <br />
                <span className="text-tertiary">Your Greatest Ally</span>
              </h1>

              <div className="bg-primary-fixed/20 border-l-4 border-primary p-4 mb-8 rounded-r-xl">
                <p className="text-body-md text-on-primary-fixed-variant italic">
                  &ldquo;Over 99% of certain cancers can be successfully treated when caught at Stage 1. We&rsquo;re here to guide you to that clarity.&rdquo;
                </p>
              </div>

              <p className="text-body-lg text-on-surface-variant mb-10 max-w-lg">
                Empower yourself with VERA&rsquo;s proactive screening and expert support. We help you gain clarity on your health status and connect you with world-class care when it matters most.
              </p>

              <div className="flex flex-col sm:flex-row gap-4">
                <StartAssessmentButton className="bg-primary text-on-primary h-12 px-8 rounded-full text-label-md shadow-lg hover:brightness-110 active:scale-95 transition-all flex items-center justify-center">
                  Start Screening Assessment
                </StartAssessmentButton>
                <Link
                  href="#how-it-works"
                  className="border-2 border-primary text-primary h-12 px-8 rounded-full text-label-md hover:bg-primary-fixed/20 transition-all flex items-center justify-center"
                >
                  How it Works
                </Link>
              </div>
            </div>

            {/* Right column — hero image */}
            <div className="relative mt-12 md:mt-0">
              <div className="absolute -top-12 -right-12 w-64 h-64 bg-secondary-container/30 rounded-full blur-3xl pointer-events-none" aria-hidden="true" />
              <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-primary-fixed/30 rounded-full blur-3xl pointer-events-none" aria-hidden="true" />
              <div className="relative rounded-3xl overflow-hidden soft-elevation aspect-[4/3]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt="A warm and reassuring scene of a healthcare professional smiling while talking with an elderly patient in a sunlit, modern medical office. The atmosphere is calm and optimistic, with soft natural light streaming through large windows. The decor uses a palette of soft teals, warm creams, and sage greens, reflecting a high-end, human-centric wellness environment."
                  className="w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBtqDXegeUPkvc26gycc8PW5Q-f2xtKaLykB-kuYZBaqCYfsowjrij7BIVL-9sdAPqfKViwUeg7NJsJqn_GSWSedfosFAoQk5jspvHFYHvhFAVBRyD7L0qSLZJRB4AVswsR00uHrzhRlVCUO47F7YgDqa8bA_QVUMiunUSdTC-9LgQ6iyxEpP1XwjJc8r7TRfnkvHimgEBmJ5_GBu5nuQlg5sRyakEbp3JW88AYeiz8nlCE1TK8KveinvMUo3DR8W1bkBmaWhMOe7Bo"
                />
              </div>
            </div>

          </div>
        </section>

        {/* ── Stats Section: Why Early Detection Matters ───────────── */}
        <section className="py-stack-lg bg-primary-fixed/10">
          <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop">
            <div className="text-center mb-16">
              <h2 className="text-headline-lg text-primary">Why Early Detection Matters</h2>
              <p className="text-body-lg text-on-surface-variant mt-4 max-w-2xl mx-auto">
                Early screening is a powerful tool for your health. When we act early, we open a world of effective options and hopeful outcomes.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="bg-surface-container-lowest p-8 rounded-2xl text-center border border-primary/10">
                <div className="text-4xl font-bold text-primary mb-2">99%</div>
                <p className="text-label-md text-primary font-semibold mb-3">Survival Rate</p>
                <p className="text-body-md text-on-surface-variant">
                  For localized breast and prostate cancers when detected at the earliest stages.
                </p>
              </div>
              <div className="bg-surface-container-lowest p-8 rounded-2xl text-center border border-primary/10">
                <div className="text-4xl font-bold text-secondary mb-2">4x</div>
                <p className="text-label-md text-secondary font-semibold mb-3">Better Outcomes</p>
                <p className="text-body-md text-on-surface-variant">
                  Early detection significantly increases the range of less-invasive treatment options available.
                </p>
              </div>
              <div className="bg-surface-container-lowest p-8 rounded-2xl text-center border border-primary/10">
                <div className="text-4xl font-bold text-tertiary mb-2">100%</div>
                <p className="text-label-md text-tertiary font-semibold mb-3">Peace of Mind</p>
                <p className="text-body-md text-on-surface-variant">
                  Regular screening provides the clarity needed to live life with confidence and focus on what matters.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── Value Proposition / Journey ──────────────────────────── */}
        <section className="py-stack-lg bg-surface-container-low" id="how-it-works">
          <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop">
            <div className="text-center mb-16">
              <span className="text-label-sm text-primary uppercase tracking-widest bg-primary-fixed/30 px-4 py-1 rounded-full">
                Our Supportive Process
              </span>
              <h2 className="text-headline-lg text-on-surface mt-4">A Three-Step Journey to Clarity</h2>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {/* Step 1 */}
              <div className="bg-surface-container-lowest p-8 rounded-3xl soft-elevation border border-outline-variant/30 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-primary-fixed flex items-center justify-center mb-6">
                  <span className="material-symbols-outlined text-primary text-3xl">medical_services</span>
                </div>
                <h3 className="text-headline-md mb-3">1. Smart Screening</h3>
                <p className="text-body-md text-on-surface-variant">
                  Start with VERA&rsquo;s personalized assessment that identifies the right screening schedule for your age and health history.
                </p>
              </div>

              {/* Step 2 */}
              <div className="bg-surface-container-lowest p-8 rounded-3xl soft-elevation border border-outline-variant/30 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-secondary-fixed flex items-center justify-center mb-6">
                  <span className="material-symbols-outlined text-secondary text-3xl">person_search</span>
                </div>
                <h3 className="text-headline-md mb-3">2. Expert Matching</h3>
                <p className="text-body-md text-on-surface-variant">
                  We connect you with vetted oncologists and specialists, ensuring you have the best professional support by your side.
                </p>
              </div>

              {/* Step 3 */}
              <div className="bg-surface-container-lowest p-8 rounded-3xl soft-elevation border border-outline-variant/30 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-tertiary-fixed flex items-center justify-center mb-6">
                  <span className="material-symbols-outlined text-tertiary text-3xl">description</span>
                </div>
                <h3 className="text-headline-md mb-3">3. Clear Summaries</h3>
                <p className="text-body-md text-on-surface-variant">
                  Upload complex medical reports and receive compassionate, plain-language summaries that focus on next steps and hope.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── Timely Guidance + CTA ────────────────────────────────── */}
        <section className="py-stack-lg">
          <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop grid grid-cols-1 md:grid-cols-2 gap-gutter">

            {/* Timely Guidance */}
            <div className="bg-primary text-on-primary rounded-3xl p-8 flex flex-col justify-between gap-8 soft-elevation">
              <div>
                <span className="material-symbols-outlined text-4xl mb-5 block" aria-hidden="true">notifications_active</span>
                <h3 className="text-headline-md mb-3">Timely Guidance</h3>
                <p className="text-body-md opacity-90">
                  Receive gentle reminders for your upcoming screenings and appointments, so you never lose track of your health journey.
                </p>
              </div>
              <div className="flex items-center gap-4 bg-white/10 px-5 py-3 rounded-xl">
                <span className="material-symbols-outlined text-secondary-fixed" aria-hidden="true">check_circle</span>
                <span className="text-label-sm">Next screening in 12 days</span>
              </div>
            </div>

            {/* Ready for clarity CTA */}
            <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-3xl p-8 flex flex-col justify-between gap-8">
              <div>
                <span className="material-symbols-outlined text-4xl text-primary mb-5 block" aria-hidden="true">rocket_launch</span>
                <h3 className="text-headline-md mb-3">Ready for total clarity?</h3>
                <p className="text-body-md text-on-surface-variant">
                  Start your early detection journey today in complete privacy with VERA.
                </p>
              </div>
              <StartAssessmentButton className="bg-primary text-on-primary px-8 py-4 rounded-full text-label-md hover:bg-primary/90 active:scale-95 transition-all text-center">
                Launch Assessment
              </StartAssessmentButton>
            </div>

          </div>
        </section>

      </main>

      <Footer />

    </div>
  );
}
