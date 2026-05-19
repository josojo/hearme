// Pure presentational component for the question detail page.
// Split out from src/app/q/[id]/page.tsx so it's trivial to unit-test without
// touching the database.

import { AggregateChart, type ByPredicate } from "./aggregate-chart";
import { countryFlag } from "@/lib/flags";
import { CONTINENT_NAMES, COUNTRY_NAMES, type Continent } from "@/lib/geo-data";

export type EnvelopeRow = {
  uniqueIdentifier: string;
  answer: string;
  disclosedPredicates: Record<string, string> | null;
  submittedAt: Date;
};

export type QuestionDetailProps = {
  question: {
    id: string;
    text: string;
    topic: string | null;
    status: string;
    scope?: "worldwide" | "continent" | "country";
    country?: string | null;
    continent?: string | null;
    createdAt: Date;
    closesAt: Date;
  };
  totalAnswers: number;
  byPredicate: ByPredicate;
  envelopes: EnvelopeRow[];
  page: number;
  pageSize: number;
  hasNextPage: boolean;
};

function fmtDate(d: Date): string {
  return d.toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

function shortId(id: string): string {
  return id.length <= 10 ? id : id.slice(0, 8) + "…";
}

function ScopePill(props: {
  scope?: "worldwide" | "continent" | "country";
  country?: string | null;
  continent?: string | null;
}) {
  if (props.scope === "country" && props.country) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800">
        <span aria-hidden>{countryFlag(props.country)}</span>
        {COUNTRY_NAMES[props.country] ?? props.country}
      </span>
    );
  }
  if (props.scope === "continent" && props.continent) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-fuchsia-100 px-2 py-0.5 text-xs font-medium text-fuchsia-800">
        <span aria-hidden>🗺️</span>
        {CONTINENT_NAMES[props.continent as Continent] ?? props.continent}
      </span>
    );
  }
  if (props.scope === "worldwide") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
        <span aria-hidden>🌍</span>
        Worldwide
      </span>
    );
  }
  return null;
}

export function QuestionDetail(props: QuestionDetailProps) {
  const { question, totalAnswers, byPredicate, envelopes, page, pageSize, hasNextPage } =
    props;

  return (
    <article className="space-y-10">
      <header className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <ScopePill
            scope={question.scope}
            country={question.country}
            continent={question.continent}
          />
          {question.topic ? (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
              #{question.topic}
            </span>
          ) : null}
          <span
            className={
              "rounded-full px-2 py-0.5 font-medium " +
              (question.status === "open"
                ? "bg-emerald-100 text-emerald-800"
                : "bg-slate-200 text-slate-700")
            }
          >
            {question.status}
          </span>
          <span className="text-slate-400">·</span>
          <span>opened {fmtDate(question.createdAt)}</span>
          <span className="text-slate-400">·</span>
          <span>closes {fmtDate(question.closesAt)}</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          {question.text}
        </h1>
      </header>

      <section>
        <div className="flex items-baseline justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Breakdown
          </h2>
          <span className="text-sm text-slate-700">
            <strong className="font-semibold text-slate-900">
              {totalAnswers}
            </strong>{" "}
            {totalAnswers === 1 ? "answer" : "answers"} total
          </span>
        </div>
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <AggregateChart total={totalAnswers} byPredicate={byPredicate} />
        </div>
      </section>

      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Answers
        </h2>
        {envelopes.length === 0 ? (
          <p className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white/60 p-6 text-sm text-slate-600">
            No envelopes recorded yet.
          </p>
        ) : (
          <ul className="mt-4 space-y-3">
            {envelopes.map((e) => (
              <li
                key={`${e.uniqueIdentifier}-${e.submittedAt.toISOString()}`}
                className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <p className="whitespace-pre-wrap text-sm text-slate-900">
                  {e.answer}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="font-mono text-slate-400">
                    user {shortId(e.uniqueIdentifier)}
                  </span>
                  <span className="text-slate-300">·</span>
                  <span>{fmtDate(e.submittedAt)}</span>
                  {e.disclosedPredicates &&
                  Object.keys(e.disclosedPredicates).length > 0 ? (
                    <>
                      <span className="text-slate-300">·</span>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(e.disclosedPredicates).map(([k, v]) => (
                          <span
                            key={k}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-700"
                          >
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    </>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}

        {(page > 1 || hasNextPage) && (
          <nav className="mt-5 flex items-center justify-between text-sm">
            {page > 1 ? (
              <a
                href={`?page=${page - 1}`}
                className="text-slate-700 underline-offset-4 hover:text-violet-700 hover:underline"
              >
                ← Newer
              </a>
            ) : (
              <span />
            )}
            <span className="text-slate-500">
              page {page} · {pageSize}/page
            </span>
            {hasNextPage ? (
              <a
                href={`?page=${page + 1}`}
                className="text-slate-700 underline-offset-4 hover:text-violet-700 hover:underline"
              >
                Older →
              </a>
            ) : (
              <span />
            )}
          </nav>
        )}
      </section>
    </article>
  );
}
