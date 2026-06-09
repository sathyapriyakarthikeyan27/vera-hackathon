"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { label: "Assessment", href: "/assessment" },
  { label: "Results", href: "/risk" },
  { label: "Find Care", href: "/care" },
  { label: "My Records", href: "/records" },
  { label: "Chat", href: "/chat" },
];

function VeraLogo() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" fill="none" className="h-9 w-auto" aria-label="VERA" role="img">
      <path d="M10 12C10 8.68629 12.6863 6 16 6H44C47.3137 6 50 8.68629 50 12V48C50 51.3137 47.3137 54 44 54H16C12.6863 54 10 51.3137 10 48V12Z" fill="#2d7d9a" fillOpacity="0.08" />
      <path d="M22 24L30 40L38 24" stroke="#2d7d9a" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M38 24C42 24 45 27 45 31C45 35 42 38 38 38" stroke="#2d7d9a" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="0.1 6" />
      <text x="65" y="39" fontFamily="Montserrat, sans-serif" fontSize="28" fontWeight="700" fill="#2d7d9a" letterSpacing="-0.5">VERA</text>
    </svg>
  );
}

export function Navbar({ right }: { right?: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-md border-b border-outline-variant/20">
      <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop h-20 flex items-center justify-between">
        <Link href="/" aria-label="VERA home">
          <VeraLogo />
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-8" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return isActive ? (
              <span
                key={item.href}
                className="text-label-md text-primary border-b-2 border-primary pb-1 font-bold"
                aria-current="page"
              >
                {item.label}
              </span>
            ) : (
              <Link
                key={item.href}
                href={item.href}
                className="text-label-md text-on-surface-variant hover:text-primary transition-colors"
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          {right && <div className="flex items-center">{right}</div>}

          {/* Mobile hamburger */}
          <button
            type="button"
            className="md:hidden flex items-center justify-center w-11 h-11 rounded-full hover:bg-surface-container transition-colors"
            aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            onClick={() => setMobileOpen((o) => !o)}
          >
            <span className="material-symbols-outlined text-on-surface" aria-hidden="true">
              {mobileOpen ? "close" : "menu"}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile nav drawer */}
      {mobileOpen && (
        <nav
          id="mobile-nav"
          aria-label="Mobile navigation"
          className="md:hidden bg-surface border-t border-outline-variant/20 px-container-padding-mobile py-4 flex flex-col gap-1"
        >
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`px-4 py-3 rounded-xl text-label-md transition-colors ${
                  isActive
                    ? "bg-primary-fixed/30 text-primary font-bold"
                    : "text-on-surface-variant hover:bg-surface-container-low hover:text-primary"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
