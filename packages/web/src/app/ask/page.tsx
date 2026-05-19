// /ask — form to create a question.
//
// Renders a client form (ask-form.tsx) that invokes the createQuestionAction
// server action. The action inserts and redirects to /q/[id].

import { AskForm } from "@/components/ask-form";

export const dynamic = "force-dynamic";

type Scope = "worldwide" | "continent" | "country";

function parseScope(raw: string | undefined): Scope {
  if (raw === "continent" || raw === "country" || raw === "worldwide") return raw;
  return "worldwide";
}

export default function AskPage({
  searchParams,
}: {
  searchParams?: { scope?: string; country?: string; continent?: string };
}) {
  const scope = parseScope(searchParams?.scope);
  const country = (searchParams?.country ?? "").toUpperCase();
  const continent = (searchParams?.continent ?? "").toUpperCase();

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
          Ask a question
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Once posted, anyone whose Hermes agent has consented to your topic
          can answer. You&apos;ll see aggregates by demographic predicate.
        </p>
      </div>
      <AskForm
        defaultScope={scope}
        defaultCountry={country}
        defaultContinent={continent}
      />
    </section>
  );
}
