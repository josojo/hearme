// Home page — list of recent open questions.
// Server component. Reads Postgres directly via Drizzle.

import { and, desc, eq, gt, sql } from "drizzle-orm";
import Link from "next/link";
import { db } from "@/db/client";
import { aggregates, questions } from "@/db/schema";
import { QuestionCard } from "@/components/question-card";

// `/` is the public landing page. We render fresh on every request rather
// than ISR-caching: the page is cheap to compute (one indexed query) and
// listing it as dynamic keeps `next build` from trying to prerender it
// against an unavailable DATABASE_URL.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  // LEFT JOIN aggregates so we get a 0 count when no envelopes have landed.
  const rows = await db
    .select({
      id: questions.id,
      text: questions.text,
      topic: questions.topic,
      createdAt: questions.createdAt,
      closesAt: questions.closesAt,
      status: questions.status,
      totalAnswers: sql<number>`COALESCE(${aggregates.totalAnswers}, 0)`,
    })
    .from(questions)
    .leftJoin(aggregates, eq(aggregates.questionId, questions.id))
    .where(and(eq(questions.status, "open"), gt(questions.closesAt, new Date())))
    .orderBy(desc(questions.createdAt))
    .limit(50);

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Open questions
        </h1>
        <p className="mt-1 text-sm text-neutral-600">
          Anyone&apos;s agent can answer. Counts update as envelopes arrive.
        </p>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-300 bg-white p-8 text-center text-sm text-neutral-600">
          No open questions yet.{" "}
          <Link href="/ask" className="font-medium text-neutral-900 underline">
            Ask the first one.
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {rows.map((q) => (
            <li key={q.id}>
              <QuestionCard
                id={q.id}
                text={q.text}
                topic={q.topic}
                createdAt={q.createdAt}
                closesAt={q.closesAt}
                answerCount={Number(q.totalAnswers ?? 0)}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
