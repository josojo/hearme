// Zeitgeist logo — a live "pulse" (seismograph) line inside an indigo→violet→cyan
// gradient tile, with a glowing node at the leading edge: the world's sentiment,
// measured in real time. Vector, no external assets.

type Props = {
  size?: number;
  className?: string;
};

export function Logo({ size = 32, className }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      className={"logo-halo " + (className ?? "")}
      aria-hidden
    >
      <defs>
        <linearGradient id="zg-grad" x1="0" y1="0" x2="48" y2="48">
          <stop offset="0%" stopColor="#4f46e5" />
          <stop offset="45%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill="url(#zg-grad)" />
      {/* The live pulse — a baseline that spikes once, like a sentiment reading. */}
      <path
        d="M8 25 H17 L21 15 L25 34 L28 22 L31 25 H39"
        stroke="white"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* The "now" node at the leading edge, with a soft halo. */}
      <circle cx="39" cy="25" r="4" fill="white" opacity="0.35" />
      <circle cx="39" cy="25" r="2.4" fill="white" />
    </svg>
  );
}

export function LogoWordmark({ size = 32 }: { size?: number }) {
  return (
    <span className="flex items-center gap-2">
      <Logo size={size} />
      <span className="bg-brand-gradient bg-clip-text text-2xl font-bold tracking-tight text-transparent">
        zeitgeist
      </span>
    </span>
  );
}
