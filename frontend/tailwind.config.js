/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        table: {
          green: "#0b6623",
          felt: "#1b4d3e",
        },
      },
    },
  },
  plugins: [],
}
