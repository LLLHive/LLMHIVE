import type { Config } from 'tailwindcss'

const config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0b0f16',
        panel: '#111827',
        'panel-alt': '#131e33',
        text: '#e6e9ef',
        'text-dim': '#9aa3b2',
        border: '#22324a',
        gold: '#ffb31a',
        'gold-light': '#ffc74d',
        metal: '#c9d2e0',
      },
      borderRadius: {
        xl: '12px',
        '2xl': '16px',
      },
      boxShadow: {
        glass: '0 8px 24px rgba(0,0,0,0.35)',
      },
      fontFamily: {
        sans: [
          'Inter','ui-sans-serif','system-ui','Segoe UI','Roboto',
          'Helvetica','Arial','Apple Color Emoji','Segoe UI Emoji'
        ],
      },
    },
  },
  plugins: [],
} satisfies Config

export default config
