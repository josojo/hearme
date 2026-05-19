import Link from "next/link";

export type QuestionCardProps = {
  id: string;
  text: string;
  topic: string | null;
  closesAt: Date;
  createdAt: Date;
  answerCount: number;
};

function fmtDate(d: Date): string {
  // Stable, locale-free formatting so server and client agree.
  return d.toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

export function QuestionCard(props: QuestionCardProps) {
  return (
    <Link
      href={`/q/${props.id}`}
      className="block rounded-lg border border-neutral-200 bg-white p-4 transition hover:border-neutral-400"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-medium text-neutral-900">
          {props.text}
        </h3>
        <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700">
          {props.answerCount} {props.answerCount === 1 ? "answer" : "answers"}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500">
        {props.topic ? (
          <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-neutral-700">
            {props.topic}
          </span>
        ) : null}
        <span>opened {fmtDate(props.createdAt)}</span>
        <span>closes {fmtDate(props.closesAt)}</span>
      </div>
    </Link>
  );
}
