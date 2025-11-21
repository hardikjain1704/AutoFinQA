/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
        },
        accent: {
          pink: 'var(--accent-pink)',
          coral: 'var(--accent-coral)',
        },
        border: {
          primary: 'var(--border-primary)',
        },
        ring: {
          primary: 'var(--border-primary)',
        },
      },
    },
  },
  plugins: [],
}