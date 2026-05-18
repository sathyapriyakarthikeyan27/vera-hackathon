function VeraLogo({ className = "h-8 w-auto" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" fill="none" className={className} aria-label="VERA" role="img">
      <path d="M10 12C10 8.68629 12.6863 6 16 6H44C47.3137 6 50 8.68629 50 12V48C50 51.3137 47.3137 54 44 54H16C12.6863 54 10 51.3137 10 48V12Z" fill="#2d7d9a" fillOpacity="0.08" />
      <path d="M22 24L30 40L38 24" stroke="#2d7d9a" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M38 24C42 24 45 27 45 31C45 35 42 38 38 38" stroke="#2d7d9a" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="0.1 6" />
      <text x="65" y="39" fontFamily="Montserrat, sans-serif" fontSize="28" fontWeight="700" fill="#2d7d9a" letterSpacing="-0.5">VERA</text>
    </svg>
  );
}

export function Footer() {
  return (
    <footer className="w-full bg-surface-container-low border-t border-outline-variant py-12 mt-stack-lg">
      <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop flex flex-col items-center gap-4 text-center">
        <VeraLogo className="h-10 w-auto opacity-80" />
        <p className="text-body-md text-on-surface-variant max-w-md leading-relaxed">
          VERA is a health awareness tool, not a medical device. Always consult a qualified doctor.
        </p>
        <p className="text-label-sm text-on-surface-variant/50">
          &copy; 2026 VERA · Built for AI Agent Olympics, Milan AI Week
        </p>
      </div>
    </footer>
  );
}
