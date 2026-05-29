// Hearme logo — a stylized soundwave inside a violet→fuchsia gradient
// "ear" silhouette. Vector, no external assets.

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
        <linearGradient id="hm-grad" x1="0" y1="0" x2="48" y2="48">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="55%" stopColor="#c026d3" />
          <stop offset="100%" stopColor="#ec4899" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill="url(#hm-grad)" />
      {/* Soundwave bars — 5 bars, varying heights, rounded caps. */}
      <g stroke="white" strokeLinecap="round" strokeWidth="3.2">
        <line x1="12" y1="20" x2="12" y2="28" />
        <line x1="18" y1="16" x2="18" y2="32" />
        <line x1="24" y1="12" x2="24" y2="36" />
        <line x1="30" y1="18" x2="30" y2="30" />
        <line x1="36" y1="22" x2="36" y2="26" />
      </g>
    </svg>
  );
}

export function LogoWordmark({ size = 32 }: { size?: number }) {
  return (
    <span className="flex items-center gap-2">
      <Logo size={size} className="h-7 w-7 sm:h-8 sm:w-8" />
      <span className="bg-brand-gradient bg-clip-text text-xl font-bold tracking-tight text-transparent sm:text-2xl">
        hearme
      </span>
    </span>
  );
}
