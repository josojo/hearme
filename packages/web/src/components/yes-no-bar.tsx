// Shared yes/no presentation primitives.
//
// Questions are yes/no, so every breakdown bar shows *how* a cohort voted
// (green = yes, rose = no) rather than just how many answered. The filled
// width still encodes magnitude (count / section max); the split inside it
// encodes the yes/no ratio.

export const YES_GRADIENT = "linear-gradient(to right, #34d399, #059669)";
export const NO_GRADIENT = "linear-gradient(to right, #fb7185, #e11d48)";

export function YesNoBar({
  yes,
  no,
  widthPct,
}: {
  yes: number;
  no: number;
  widthPct: number;
}) {
  const total = yes + no;
  const yesPct = total === 0 ? 0 : (yes / total) * 100;
  return (
    <div className="relative h-3 w-full overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200/60">
      <div
        className="flex h-full overflow-hidden rounded-full transition-[width] duration-300"
        style={{ width: `${widthPct}%` }}
      >
        <div style={{ width: `${yesPct}%`, background: YES_GRADIENT }} />
        <div style={{ width: `${100 - yesPct}%`, background: NO_GRADIENT }} />
      </div>
    </div>
  );
}

/** Inline "Yes N · No M" counter, tabular for alignment. */
export function YesNoCount({ yes, no }: { yes: number; no: number }) {
  return (
    <span className="tabular-nums">
      <span className="font-semibold text-emerald-700">{yes}</span>
      <span className="text-slate-400"> yes</span>
      <span className="mx-1 text-slate-300">·</span>
      <span className="font-semibold text-rose-700">{no}</span>
      <span className="text-slate-400"> no</span>
    </span>
  );
}

/** Small legend explaining the colour coding; rendered once per page. */
export function YesNoLegend() {
  return (
    <div className="flex items-center gap-4 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1.5">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ background: YES_GRADIENT }}
        />
        Yes
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ background: NO_GRADIENT }}
        />
        No
      </span>
    </div>
  );
}
