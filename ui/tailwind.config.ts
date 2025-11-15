import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./ui/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f16",
        panel: "#111827",
        "panel-alt": "#131e33",
        text: "#e6e9ef",
        "text-dim": "#9aa3b2",
        border: "#22324a",
        metal: "#c9d2e0",
        gold: "#ffb31a",
        "gold-light": "#ffc74d",
        // semantic
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
        // aliases (keep both old & new keys to avoid regressions)
        panelAlt: "#131e33",
        textDim: "#9aa3b2",
        primary: "#ffb31a",
        "primary-light": "#ffc74d"
      },
      borderRadius: {
        xl: "12px",
        "2xl": "16px"
      }
    }
  },
  plugins: []
};

export default config;
