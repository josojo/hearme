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
        brand: {
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
          700: "#6d28d9",
          800: "#5b21b6",
          900: "#4c1d95",
        },
      },
      boxShadow: {
        glow: "0 10px 40px -10px rgb(124 58 237 / 0.45)",
      },
      backgroundImage: {
        "brand-gradient":
          "linear-gradient(135deg, #7c3aed 0%, #c026d3 50%, #ec4899 100%)",
        "mesh":
          "radial-gradient(at 20% 0%, rgba(124,58,237,0.15) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(236,72,153,0.12) 0px, transparent 50%), radial-gradient(at 50% 100%, rgba(45,212,191,0.08) 0px, transparent 50%)",
      },
    },
  },
  plugins: [],
};

export default config;
