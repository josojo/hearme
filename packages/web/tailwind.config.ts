import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        // The layout loads Inter via next/font and wires it through this var.
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: [
          "var(--font-inter)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        // Zeitgeist "live signal" brand ramp: indigo → cyan.
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },
      },
      boxShadow: {
        glow: "0 10px 40px -10px rgb(79 70 229 / 0.45)",
      },
      backgroundImage: {
        // The signal gradient: indigo → violet → live cyan.
        "brand-gradient":
          "linear-gradient(135deg, #4f46e5 0%, #7c3aed 45%, #06b6d4 100%)",
        "mesh":
          "radial-gradient(at 20% 0%, rgba(79,70,229,0.15) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(6,182,212,0.12) 0px, transparent 50%), radial-gradient(at 50% 100%, rgba(124,58,237,0.08) 0px, transparent 50%)",
      },
    },
  },
  plugins: [],
};

export default config;
