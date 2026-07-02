import Link from "next/link";

function VeraLogo({ className = "h-12 w-auto" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" fill="none" className={className} aria-label="VERA" role="img">
      <path d="M10 12C10 8.68629 12.6863 6 16 6H44C47.3137 6 50 8.68629 50 12V48C50 51.3137 47.3137 54 44 54H16C12.6863 54 10 51.3137 10 48V12Z" fill="#2d7d9a" fillOpacity="0.08" />
      <path d="M22 24L30 40L38 24" stroke="#2d7d9a" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M38 24C42 24 45 27 45 31C45 35 42 38 38 38" stroke="#2d7d9a" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="0.1 6" />
      <text x="65" y="39" fontFamily="Montserrat, sans-serif" fontSize="28" fontWeight="700" fill="#2d7d9a" letterSpacing="-0.5">VERA</text>
    </svg>
  );
}

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="w-full py-8 flex justify-center">
        <Link href="/" aria-label="VERA home">
          <VeraLogo className="h-12 w-auto" />
        </Link>
      </header>

      <main
        id="main-content"
        className="flex-1 flex items-start justify-center px-container-padding-mobile pb-16"
      >
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-headline-lg text-on-surface mb-2">{title}</h1>
            {subtitle && (
              <p className="text-body-md text-on-surface-variant">{subtitle}</p>
            )}
          </div>
          <div className="bg-surface-container-lowest border border-outline-variant rounded-3xl p-8 soft-elevation">
            {children}
          </div>
        </div>
      </main>

      <footer className="py-8 text-center">
        <p className="text-label-sm text-on-surface-variant/60 max-w-md mx-auto px-6 leading-relaxed">
          VERA is a health awareness tool, not a medical device. Always consult a qualified doctor.
        </p>
      </footer>
    </div>
  );
}

/** Full-page Google OAuth button (anchor, not fetch — it redirects). */
export function GoogleButton({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl border border-outline bg-surface-container-lowest text-body-md font-medium text-on-surface hover:bg-surface-container-low transition-colors min-h-[48px]"
    >
      <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
      </svg>
      {label}
    </a>
  );
}
