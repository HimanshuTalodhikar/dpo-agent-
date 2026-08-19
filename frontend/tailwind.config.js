/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#000000',
          900: '#09090b',
          850: '#121215',
          800: '#18181b',
          700: '#27272a',
        },
        border: 'rgba(255, 255, 255, 0.16)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['Outfit', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-white': '0 0 25px rgba(255, 255, 255, 0.25)',
        'glow-white-lg': '0 0 40px rgba(255, 255, 255, 0.4)',
        'glass': '0 10px 40px 0 rgba(0, 0, 0, 0.85)',
      },
      animation: {
        'spin-slow': 'spin 12s linear infinite',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 15px rgba(255, 255, 255, 0.2)' },
          '50%': { boxShadow: '0 0 30px rgba(255, 255, 255, 0.5)' },
        },
      },
    },
  },
  plugins: [],
}
