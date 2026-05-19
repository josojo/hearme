// Tiny horizontal bar list rendering aggregates.by_predicate.
//
// Schema (ARCHITECTURE.md §3): `by_predicate JSONB`, e.g.
//   { "region:EU": 42, "region:non-EU": 18, "age_band:25-34": 30 }
//
// We group entries by the predicate key (before the ':') so the user sees
// a section per dimension. Within a section the values are bars proportional
// to the section's max.

export type ByPredicate = Record<string, number>;

export type AggregateChartProps = {
  total: number;
  byPredicate: ByPredicate;
};

type Grouped = Record<string, Array<{ value: string; count: number }>>;

export function groupByDimension(byPredicate: ByPredicate): Grouped {
  const out: Grouped = {};
  for (const [k, raw] of Object.entries(byPredicate)) {
    if (typeof raw !== "number" || !Number.isFinite(raw)) continue;
    // Keys look like "dimension:value"; if no ':' is present treat the whole
    // key as the value under a dimension called "other".
    const idx = k.indexOf(":");
    const dim = idx === -1 ? "other" : k.slice(0, idx);
    const value = idx === -1 ? k : k.slice(idx + 1);
    if (!out[dim]) out[dim] = [];
    out[dim].push({ value, count: raw });
  }
  for (const dim of Object.keys(out)) {
    out[dim].sort((a, b) => b.count - a.count);
  }
  return out;
}

export function AggregateChart({ total, byPredicate }: AggregateChartProps) {
  const grouped = groupByDimension(byPredicate);
  const dims = Object.keys(grouped).sort();

  if (total === 0 || dims.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-neutral-300 bg-white p-4 text-sm text-neutral-600">
        No answers yet. Agents poll the broker every ~30s for new questions.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {dims.map((dim) => {
        const entries = grouped[dim];
        const sectionMax = entries.reduce(
          (m, e) => (e.count > m ? e.count : m),
          0,
        );
        return (
          <div key={dim}>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-neutral-500">
              {dim}
            </h3>
            <ul className="space-y-1">
              {entries.map((e) => {
                const pct = sectionMax === 0 ? 0 : (e.count / sectionMax) * 100;
                return (
                  <li
                    key={e.value}
                    className="flex items-center gap-3 text-sm"
                  >
                    <span className="w-28 shrink-0 truncate text-neutral-700">
                      {e.value}
                    </span>
                    <div className="relative h-4 flex-1 overflow-hidden rounded bg-neutral-100">
                      <div
                        className="h-full bg-neutral-800"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-10 shrink-0 text-right tabular-nums text-neutral-700">
                      {e.count}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
