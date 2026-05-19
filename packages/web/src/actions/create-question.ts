"use server";

// /ask server action.
//
// Inserts an asker display row and a question, then redirects to /q/[id].
// The web role is allowed INSERT on `askers` and `questions` only (see
// db/init/02-roles.sql).
//
// This action MUST NOT write to envelopes or aggregates. The DB grants
// enforce that, but we don't even attempt it here.
//
// Pure validation lives in ./validate-question.ts so non-server code can
// import it (the "use server" rule forces every export of this module to
// be an async function).

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { db } from "@/db/client";
import { askers, questions } from "@/db/schema";
import {
  validateCreateQuestion,
  type CreateQuestionInput,
} from "./validate-question";

export type CreateQuestionResult =
  | { ok: true; questionId: string }
  | { ok: false; errors: Record<string, string> };

/**
 * Pure DB insertion helper. Exposed so tests can exercise the happy path
 * without going through the form-action signature.
 */
export async function createQuestion(
  input: CreateQuestionInput,
  dbi: typeof db = db,
): Promise<{ questionId: string }> {
  // v0 display names are not identity. Create one display row per question
  // so two humans choosing the same name are not collapsed together.
  const askerRows = await dbi
    .insert(askers)
    .values({ displayName: input.displayName })
    .returning({ id: askers.id });
  const askerId = askerRows[0].id;

  const inserted = await dbi
    .insert(questions)
    .values({
      askerId,
      text: input.text,
      topic: input.topic ?? null,
      closesAt: input.closesAt,
      // status defaults to 'open'; nonce defaults to a random base64 blob.
    })
    .returning({ id: questions.id });

  return { questionId: inserted[0].id };
}

/**
 * Server action invoked by `<form action={...}>`. Validates the FormData,
 * inserts the row, then redirects.
 */
export async function createQuestionAction(
  _prevState: unknown,
  formData: FormData,
): Promise<CreateQuestionResult> {
  const closesAtIso = (formData.get("closesAtIso") ?? "").toString();
  const closesAtRaw = (formData.get("closesAt") ?? "").toString();
  const parsedDate = closesAtIso
    ? new Date(closesAtIso)
    : closesAtRaw
      ? new Date(closesAtRaw)
      : null;

  const parsed = validateCreateQuestion({
    displayName: (formData.get("displayName") ?? "").toString(),
    text: (formData.get("text") ?? "").toString(),
    topic: (formData.get("topic") ?? "").toString(),
    closesAt: parsedDate ?? undefined,
  });

  if (!parsed.ok) {
    return { ok: false, errors: parsed.errors };
  }

  const { questionId } = await createQuestion(parsed.value);

  // Force the home feed to refetch so the new question shows up immediately.
  revalidatePath("/");
  redirect(`/q/${questionId}`);
}
