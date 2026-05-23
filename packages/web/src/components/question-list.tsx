"use client";

// Client-side search over the open-questions feed. The server hands us the
// already-scoped rows; we filter them live by the words typed in the box.

import { useMemo, useState } from "react";
import { QuestionCard } from "@/components/question-card";
import type { Scope } from "@/components/scope-tabs";

export type QuestionListItem = {
  id: string;
  text: string;
  topic: string | null;
  scope: Scope;
  country: string | null;
  continent: string | null;
  createdAt: Date;
  closesAt: Date;
  answerCount: number;
};

export function QuestionList({ items }: { items: QuestionListItem[] }) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (terms.length === 0) return items;
    return items.filter((q) => {
      const haystack = `${q.text} ${q.topic ?? ""}`.toLowerCase();
      // Every typed word must appear somewhere in the question.
      return terms.every((t) => haystack.includes(t));
    });
  }, [items, query]);

  return (
    <div className="space-y-4">
      <div className="relative">
        <span
          aria-hidden
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path
              fillRule="evenodd"
              d="M9 3.5a5.5 5.5 0 1 0 3.473 9.766l3.13 3.131a.75.75 0 1 0 1.061-1.06l-3.13-3.132A5.5 5.5 0 0 0 9 3.5ZM5 9a4 4 0 1 1 8 0 4 4 0 0 1-8 0Z"
              clipRule="evenodd"
            />
          </svg>
        </span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search questions…"
          aria-label="Search questions"
          className="block w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm shadow-sm transition focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100"
        />
      </div>

      {query.trim() ? (
        <p className="px-1 text-xs text-slate-500">
          {filtered.length === 0
            ? "No questions match your search."
            : `${filtered.length} of ${items.length} ${
                items.length === 1 ? "question" : "questions"
              }`}
        </p>
      ) : null}

      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center">
          <p className="text-sm text-slate-600">
            Nothing matches{" "}
            <strong className="text-slate-900">“{query.trim()}”</strong>. Try
            different words.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {filtered.map((q) => (
            <li key={q.id}>
              <QuestionCard
                id={q.id}
                text={q.text}
                topic={q.topic}
                scope={q.scope}
                country={q.country}
                continent={q.continent}
                createdAt={q.createdAt}
                closesAt={q.closesAt}
                answerCount={q.answerCount}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
