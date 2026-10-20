/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        cinema: {
          950: "#07090e",
          900: "#0d111a",
          800: "#151c2c",
          700: "#1f2940",
          ivory: "#f4efe6",
          sand: "#e7dfd2",
          accent: "#f59e0b",
          crimson: "#e11d48",
          teal: "#2dd4bf",
        },
      },
      boxShadow: {
        glow: "0 0 24px rgba(245, 158, 11, 0.35)",
        "glow-teal": "0 0 22px rgba(45, 212, 191, 0.35)",
      },
    },
  },
  plugins: [],
};
