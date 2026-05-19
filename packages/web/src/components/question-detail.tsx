// Pure presentational component for the question detail page.
// Split out from src/app/q/[id]/page.tsx so it's trivial to unit-test without
// touching the database.

import { AggregateChart, type ByPredicate } from "./aggregate-chart";

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
  // Show a short prefix of the (hex/base64) unique_identifier so individual
  // envelopes are distinguishable in the UI without leaking the full handle.
  return id.length <= 10 ? id : id.slice(0, 8) + "…";
}

export function QuestionDetail(props: QuestionDetailProps) {
  const { question, totalAnswers, byPredicate, envelopes, page, pageSize, hasNextPage } =
    props;

  return (
    <article className="space-y-8">
      <header className="space-y-3">
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          {question.topic ? (
            <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-neutral-700">
              {question.topic}
            </span>
          ) : null}
          <span>opened {fmtDate(question.createdAt)}</span>
          <span>closes {fmtDate(question.closesAt)}</span>
          <span
            className={
              question.status === "open"
                ? "rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-800"
                : "rounded bg-neutral-200 px-1.5 py-0.5 text-neutral-700"
            }
          >
            {question.status}
          </span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          {question.text}
        </h1>
      </header>

      <section>
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
            Breakdown
          </h2>
          <span className="text-sm text-neutral-700">
            <strong className="font-semibold">{totalAnswers}</strong>{" "}
            {totalAnswers === 1 ? "answer" : "answers"} total
          </span>
        </div>
        <div className="mt-3">
          <AggregateChart total={totalAnswers} byPredicate={byPredicate} />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
          Answers
        </h2>
        {envelopes.length === 0 ? (
          <p className="mt-3 text-sm text-neutral-600">
            No envelopes recorded yet.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {envelopes.map((e) => (
              <li
                key={`${e.uniqueIdentifier}-${e.submittedAt.toISOString()}`}
                className="rounded-md border border-neutral-200 bg-white p-3"
              >
                <p className="whitespace-pre-wrap text-sm text-neutral-900">
                  {e.answer}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-neutral-500">
                  <span className="font-mono">
                    user {shortId(e.uniqueIdentifier)}
                  </span>
                  <span>•</span>
                  <span>{fmtDate(e.submittedAt)}</span>
                  {e.disclosedPredicates &&
                  Object.keys(e.disclosedPredicates).length > 0 ? (
                    <>
                      <span>•</span>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(e.disclosedPredicates).map(([k, v]) => (
                          <span
                            key={k}
                            className="rounded bg-neutral-100 px-1.5 py-0.5 text-neutral-700"
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
          <nav className="mt-4 flex items-center justify-between text-sm">
            {page > 1 ? (
              <a
                href={`?page=${page - 1}`}
                className="text-neutral-700 underline hover:text-neutral-900"
              >
                ← Newer
              </a>
            ) : (
              <span />
            )}
            <span className="text-neutral-500">
              page {page} · {pageSize}/page
            </span>
            {hasNextPage ? (
              <a
                href={`?page=${page + 1}`}
                className="text-neutral-700 underline hover:text-neutral-900"
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
