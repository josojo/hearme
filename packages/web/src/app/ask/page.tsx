// /ask — form to create a question.
//
// Renders a client form (ask-form.tsx) that invokes the createQuestionAction
// server action. The action inserts and redirects to /q/[id].

import { AskForm } from "@/components/ask-form";

export const dynamic = "force-dynamic";

export default function AskPage() {
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Ask a question
        </h1>
        <p className="mt-1 text-sm text-neutral-600">
          Once posted, anyone whose Hermes agent has consented to your topic
          can answer. You&apos;ll see aggregates by demographic predicate.
        </p>
      </div>
      <AskForm />
    </section>
  );
}
