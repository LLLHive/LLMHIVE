import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: false,
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#ffffff",
        panel: "#f7f8fa",
        panelAlt: "#eceff4",
        text: "#1f2937",
        textDim: "#6b7280",
        primary: "#ffb31a",
        primaryLight: "#ffc74d",
        border: "#d1d5db",
        success: "#1f9d55",
        warning: "#b7791f",
        danger: "#dc2626",
      },
      borderRadius: {
        card: "8px",
        button: "16px",
        xl: "24px",
      },
      boxShadow: {
        sm: "0 1px 3px rgba(0,0,0,0.1)",
        lg: "0 4px 20px rgba(0,0,0,0.1)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "Plus Jakarta Sans",
          "Roboto Flex",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      transitionTimingFunction: {
        soft: "cubic-bezier(0.22,0.61,0.36,1)",
      },
    },
  },
  plugins: [],
};

export default config;
