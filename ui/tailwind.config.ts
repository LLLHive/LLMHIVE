import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b1220",
        panel: "#0f1a2b",
        panel2: "#131e33",
        text: "#e6e9ef",
        textdim: "#a8b1c4",
        primary: "#ffb31a",
        primary2: "#ffc74d",
        border: "#22324a",
        glassStroke: "#c9d2e0",
        success: "#2dd4bf",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
      borderRadius: {
        xl: "24px",
        lg: "16px",
      },
      boxShadow: {
        app1: "0 2px 8px rgba(0,0,0,.35)",
        app2: "0 6px 24px rgba(0,0,0,.45)",
      },
      transitionTimingFunction: {
        app: "cubic-bezier(.22,.61,.36,1)",
      },
      transitionDuration: {
        app1: "160ms",
        app2: "260ms",
      },
    },
  },
  plugins: [],
};

export default config;
