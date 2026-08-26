/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Elicit Theme
        background: '#FAFAFA',
        secondary: '#FFFFFF',
        primary: '#1B6D7A',
        text: '#111827',
        accent: '#D1E8E6',
        sidebar: '#F9FAFB',
        border: '#E5E7EB'
      }
    },
  },
  plugins: [],
}
