// /q/[id] — question detail.
//
// Server component. Reads:
//   - the question row
//   - its aggregates row (total + by_predicate)
// Raw envelopes remain broker-private; the public page shows aggregates only.
//
// Per ARCHITECTURE.md §4, we use Next.js `revalidate` (10s) instead of
// websockets / SSE — that's a v0.2 upgrade documented in §11.

import { eq } from "drizzle-orm";
import { notFound } from "next/navigation";
import { db } from "@/db/client";
import { aggregates, questions } from "@/db/schema";
import { QuestionDetail } from "@/components/question-detail";
import type { ByPredicate } from "@/components/aggregate-chart";

export const revalidate = 10;

type PageProps = {
  params: { id: string };
};

export default async function QuestionPage({ params }: PageProps) {
  const questionRows = await db
    .select()
    .from(questions)
    .where(eq(questions.id, params.id))
    .limit(1);

  if (questionRows.length === 0) {
    notFound();
  }
  const question = questionRows[0];
  const effectiveStatus =
    question.status === "open" && question.closesAt > new Date()
      ? "open"
      : "closed";

  const aggRows = await db
    .select()
    .from(aggregates)
    .where(eq(aggregates.questionId, params.id))
    .limit(1);

  const totalAnswers = aggRows[0]?.totalAnswers ?? 0;
  const byPredicate =
    (aggRows[0]?.byPredicate as ByPredicate | null) ?? ({} as ByPredicate);

  return (
    <QuestionDetail
      question={{
        id: question.id,
        text: question.text,
        topic: question.topic,
        status: effectiveStatus,
        scope: question.scope as "worldwide" | "continent" | "country",
        country: question.country,
        continent: question.continent,
        createdAt: question.createdAt,
        closesAt: question.closesAt,
      }}
      totalAnswers={totalAnswers}
      byPredicate={byPredicate}
    />
  );
}
