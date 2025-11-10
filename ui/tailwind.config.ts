import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0b0f16',
        panel: '#111827',
        panelAlt: '#131e33',
        text: '#e6e9ef',
        textDim: '#9aa3b2',
        border: '#22324a',
        gold: '#ffb31a',
        goldLight: '#ffc74d',
        metal: '#c9d2e0',
        primary: "#ffb31a",
        primaryLight: "#ffc74d",
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
