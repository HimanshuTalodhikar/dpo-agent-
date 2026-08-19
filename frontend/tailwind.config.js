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
          900: '#0a0a05',
          850: '#12110b',
          800: '#1a180e',
          700: '#262314',
        },
        gold: {
          300: '#FDE047',
          400: '#FACC15',
          500: '#EAB308',
          600: '#CA8A04',
          700: '#A16207',
          800: '#854D0E',
          900: '#713F12',
          950: '#451A03',
        },
        border: 'rgba(245, 158, 11, 0.25)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['Orbitron', 'Rajdhani', 'sans-serif'],
        robot: ['Orbitron', 'monospace'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-gold': '0 0 25px rgba(245, 158, 11, 0.4)',
        'glow-gold-lg': '0 0 45px rgba(245, 158, 11, 0.65)',
        'glow-amber': '0 0 30px rgba(217, 119, 6, 0.5)',
        'glass': '0 10px 40px 0 rgba(0, 0, 0, 0.95)',
      },
      animation: {
        'spin-slow': 'spin 12s linear infinite',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'scanner': 'scanner 3s ease-in-out infinite',
        'float': 'float 4s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 15px rgba(245, 158, 11, 0.3)' },
          '50%': { boxShadow: '0 0 35px rgba(245, 158, 11, 0.7)' },
        },
        scanner: {
          '0%, 100%': { transform: 'translateY(-10px)', opacity: '0.4' },
          '50%': { transform: 'translateY(80px)', opacity: '1' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}
