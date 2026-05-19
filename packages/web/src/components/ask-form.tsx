"use client";

import { useEffect, useState } from "react";
import { useFormState, useFormStatus } from "react-dom";
import {
  createQuestionAction,
  type CreateQuestionResult,
} from "@/actions/create-question";

const initialState: CreateQuestionResult | null = null;

function toLocalDatetimeValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

function toUtcIso(localValue: string): string {
  const d = new Date(localValue);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString();
}

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {pending ? "Posting…" : "Post question"}
    </button>
  );
}

export function AskForm() {
  // `useFormState` is the App Router pattern for surfacing server-action
  // results back into the form (validation errors, in our case).
  const [state, formAction] = useFormState(
    // The signature `(prev, formData) => Promise<Result>` matches our action.
    createQuestionAction as unknown as (
      prev: CreateQuestionResult | null,
      data: FormData,
    ) => Promise<CreateQuestionResult>,
    initialState,
  );

  const errors = state && state.ok === false ? state.errors : {};
  const [closesAt, setClosesAt] = useState("");
  const closesAtIso = closesAt ? toUtcIso(closesAt) : "";

  useEffect(() => {
    setClosesAt(
      toLocalDatetimeValue(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)),
    );
  }, []);

  return (
    <form action={formAction} className="space-y-4">
      <Field
        label="Your display name"
        name="displayName"
        hint="No accounts yet. Anyone can pick any name. (v0)"
        error={errors.displayName}
      >
        <input
          type="text"
          name="displayName"
          maxLength={80}
          required
          className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-neutral-900 focus:outline-none"
        />
      </Field>

      <Field
        label="Question"
        name="text"
        hint="A clear, single question the agents can answer."
        error={errors.text}
      >
        <textarea
          name="text"
          rows={4}
          maxLength={2000}
          required
          className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-neutral-900 focus:outline-none"
        />
      </Field>

      <Field
        label="Topic (optional)"
        name="topic"
        hint="A short tag — e.g. ‘politics’, ‘food’. Agents filter on this."
        error={errors.topic}
      >
        <input
          type="text"
          name="topic"
          maxLength={80}
          className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-neutral-900 focus:outline-none"
        />
      </Field>

      <Field
        label="Closes at"
        name="closesAt"
        hint="When to stop accepting answers."
        error={errors.closesAt}
      >
        <input
          type="datetime-local"
          name="closesAt"
          value={closesAt}
          onChange={(e) => setClosesAt(e.target.value)}
          required
          className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-neutral-900 focus:outline-none"
        />
        <input type="hidden" name="closesAtIso" value={closesAtIso} />
      </Field>

      <SubmitButton />
    </form>
  );
}

function Field({
  label,
  name,
  hint,
  error,
  children,
}: {
  label: string;
  name: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label
        htmlFor={name}
        className="block text-sm font-medium text-neutral-900"
      >
        {label}
      </label>
      <div className="mt-1">{children}</div>
      {error ? (
        <p className="mt-1 text-xs text-red-600">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-xs text-neutral-500">{hint}</p>
      ) : null}
    </div>
  );
}
