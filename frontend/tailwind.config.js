/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dark theme base
        dark: {
          bg: '#0a0a0a',
          card: '#18181b',
          'card-hover': '#27272a',
          border: '#27272a',
        },
        // Sentiment colors
        bullish: {
          DEFAULT: '#10b981',
          light: '#34d399',
          dark: '#059669',
          bg: 'rgba(16, 185, 129, 0.15)',
        },
        bearish: {
          DEFAULT: '#f43f5e',
          light: '#fb7185',
          dark: '#e11d48',
          bg: 'rgba(244, 63, 94, 0.15)',
        },
        neutral: {
          DEFAULT: '#fbbf24',
          light: '#fcd34d',
          dark: '#f59e0b',
          bg: 'rgba(251, 191, 36, 0.15)',
        },
        // Accent colors
        accent: {
          cyan: '#22d3ee',
          'cyan-dark': '#06b6d4',
          purple: '#a855f7',
        },
        // Sector colors
        sector: {
          banking: '#60a5fa',
          it: '#c084fc',
          pharma: '#2dd4bf',
          auto: '#fb923c',
          energy: '#facc15',
          fmcg: '#f472b6',
          metals: '#d1d5db',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
