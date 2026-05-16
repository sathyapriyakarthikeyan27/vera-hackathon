import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "VERA — Vital Early Risk Advisor",
  description:
    "Your personal cancer risk companion. Understand your risk, find free care near you, and take action early.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={geist.variable}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
