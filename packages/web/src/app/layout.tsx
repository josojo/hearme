import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import type { ReactNode } from "react";
import { LogoWordmark } from "@/components/logo";
import { HowItWorks } from "@/components/how-it-works";
import { EarnExplainer } from "@/components/earn-explainer";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Zeitgeist — the world's mind, in real time",
  description:
    "Measure the spirit of the times. Ask a question and real humans' agents answer on their behalf, with verified demographic predicates — watch global sentiment shift live, worldwide, by continent, or by country.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans">
        <div className="mx-auto max-w-4xl px-4 py-6 sm:py-10">
          <header className="mb-10 flex items-center justify-between border-b border-slate-200/70 pb-5">
            <Link href="/" className="flex items-center" aria-label="Zeitgeist home">
              <LogoWordmark />
            </Link>
            <nav className="flex items-center gap-1.5 sm:gap-3 text-sm">
              <HowItWorks />
              <EarnExplainer />
              <Link
                href="/"
                className="rounded-full px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-100"
              >
                Questions
              </Link>
              <Link
                href="/ask"
                className="inline-flex items-center gap-1.5 rounded-full bg-brand-gradient px-4 py-2 font-medium text-white shadow-glow transition hover:opacity-95"
              >
                <span aria-hidden>+</span> Ask
              </Link>
            </nav>
          </header>
          <main>{children}</main>
          <footer className="mt-20 border-t border-slate-200/70 pt-6 text-xs text-slate-500">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                Zeitgeist v0 — the spirit of the times, measured live.
              </span>
              <span className="text-slate-400">
                Real answers, verified humans, no surveillance.
              </span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
