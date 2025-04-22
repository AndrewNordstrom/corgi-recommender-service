/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        primary: {
          DEFAULT: '#ffb300', // amber
          light: '#ffd54f',
          dark: '#ff8f00',
        },
        accent: {
          DEFAULT: '#ff5722', // deep orange
          light: '#ff8a65',
          dark: '#e64a19',
        },
        background: {
          light: '#fffbf5',
          dark: '#1a1a1a',
        },
        navy: '#1a237e',
        neutral: {
          50: '#faf6f1',
          100: '#f5efe8',
          200: '#e8e0d5',
          300: '#d5c9ba',
          400: '#b3a799',
          500: '#8c7b6a',
          600: '#6f5f4d',
          700: '#564a3c',
          800: '#423931',
          900: '#342c23',
        }
      },
      boxShadow: {
        'card': '0 2px 8px 0 rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 15px 0 rgba(0, 0, 0, 0.08)',
      },
      borderRadius: {
        'card': '8px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'shine': 'shine 2s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shine: {
          '0%': { left: '-100%' },
          '100%': { left: '100%' },
        },
      },
    },
  },
  plugins: [],
}