/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f0f4ff',
          100: '#e0e9ff',
          200: '#c7d7fe',
          300: '#a5b9fd',
          400: '#7f91fb',
          500: '#6269f5',
          600: '#4f49e8',
          700: '#3d37cc',
          800: '#2d2898',
          900: '#1e1a6e',
          950: '#0f0d40',
        },
        primary: {
          50: '#f0f4ff',
          100: '#dce8ff',
          200: '#b9d0ff',
          300: '#8caefc',
          400: '#6089f8',
          500: '#3b62f2',
          600: '#1e3ea8',
          700: '#172e82',
          800: '#0f1f5c',
          900: '#081238',
          950: '#040a1f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 12px 0 rgba(0,0,0,0.08)',
        'card-hover': '0 4px 24px 0 rgba(0,0,0,0.14)',
      },
    },
  },
  plugins: [],
}
