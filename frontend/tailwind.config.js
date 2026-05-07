/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        syne: ['Syne', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        surface: {
          950: '#080c0a',
          900: '#0a0f0c',
          800: '#0d1710',
          700: '#111c14',
          600: '#172219',
          500: '#1a2e24',
        },
        teal: {
          950: '#04342C',
          900: '#085041',
          800: '#0F6E56',
          700: '#0F6E56',
          600: '#1D9E75',
          500: '#1D9E75',
          400: '#5DCAA5',
          300: '#9FE1CB',
          200: '#E1F5EE',
        }
      }
    },
  },
  plugins: [],
}