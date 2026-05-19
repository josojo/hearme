import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Hearme",
  description:
    "Ask a question. Real humans' agents answer on their behalf, with verified demographic predicates.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-3xl px-4 py-6">
          <header className="mb-8 flex items-center justify-between border-b border-neutral-200 pb-4">
            <Link
              href="/"
              className="text-xl font-semibold tracking-tight text-neutral-900"
            >
              hearme
            </Link>
            <nav className="flex items-center gap-4 text-sm">
              <Link
                href="/"
                className="text-neutral-600 hover:text-neutral-900"
              >
                Questions
              </Link>
              <Link
                href="/ask"
                className="rounded-md bg-neutral-900 px-3 py-1.5 text-white hover:bg-neutral-700"
              >
                Ask
              </Link>
            </nav>
          </header>
          <main>{children}</main>
          <footer className="mt-16 border-t border-neutral-200 pt-4 text-xs text-neutral-500">
            v0 — no auth, no payments, polling every 10s on detail pages.
          </footer>
        </div>
      </body>
    </html>
  );
}
