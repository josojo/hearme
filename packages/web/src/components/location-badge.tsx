import type { Location } from "@/lib/geo";
import { countryFlag } from "@/lib/flags";

type Props = {
  location: Location;
};

const SOURCE_LABEL: Record<Location["source"], string> = {
  override: "manually set",
  header: "from your network",
  lookup: "from your IP",
  default: "default",
};

export function LocationBadge({ location }: Props) {
  return (
    <div
      className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 shadow-sm"
      title={`Detected ${SOURCE_LABEL[location.source]}`}
    >
      <span className="text-base leading-none" aria-hidden>
        {countryFlag(location.country)}
      </span>
      <span className="font-medium text-slate-900">{location.countryName}</span>
      <span className="text-slate-400">·</span>
      <span className="text-slate-500">{location.continentName}</span>
    </div>
  );
}
