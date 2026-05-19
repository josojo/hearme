// /q/[id] — question detail.
//
// Server component. Reads:
//   - the question row
//   - its aggregates row (total + by_predicate)
//   - a paginated slice of envelopes (newest first)
//
// Per ARCHITECTURE.md §4, we use Next.js `revalidate` (10s) instead of
// websockets / SSE — that's a v0.2 upgrade documented in §11.

import { desc, eq } from "drizzle-orm";
import { notFound } from "next/navigation";
import { db } from "@/db/client";
import { aggregates, envelopes, questions } from "@/db/schema";
import {
  QuestionDetail,
  type EnvelopeRow,
} from "@/components/question-detail";
import type { ByPredicate } from "@/components/aggregate-chart";

export const revalidate = 10;

const PAGE_SIZE = 25;

type PageProps = {
  params: { id: string };
  searchParams?: { page?: string };
};

function parsePage(raw: string | undefined): number {
  if (!raw) return 1;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return 1;
  return n;
}

export default async function QuestionPage({ params, searchParams }: PageProps) {
  const page = parsePage(searchParams?.page);
  const offset = (page - 1) * PAGE_SIZE;

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

  // Fetch one extra row so we can tell whether there's a next page.
  const envelopeRows = await db
    .select({
      uniqueIdentifier: envelopes.uniqueIdentifier,
      answer: envelopes.answer,
      disclosedPredicates: envelopes.disclosedPredicates,
      submittedAt: envelopes.submittedAt,
    })
    .from(envelopes)
    .where(eq(envelopes.questionId, params.id))
    .orderBy(desc(envelopes.submittedAt))
    .limit(PAGE_SIZE + 1)
    .offset(offset);

  const hasNextPage = envelopeRows.length > PAGE_SIZE;
  const pageRows: EnvelopeRow[] = envelopeRows.slice(0, PAGE_SIZE).map((r) => ({
    uniqueIdentifier: r.uniqueIdentifier,
    answer: r.answer,
    disclosedPredicates:
      (r.disclosedPredicates as Record<string, string> | null) ?? null,
    submittedAt: r.submittedAt,
  }));

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
      envelopes={pageRows}
      page={page}
      pageSize={PAGE_SIZE}
      hasNextPage={hasNextPage}
    />
  );
}
