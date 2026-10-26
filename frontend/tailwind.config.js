/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#132c2c",
        muted: "#637575",
        canvas: "#f4f7f6",
        teal: { 50: "#eef8f6", 100: "#d9efeb", 500: "#3d9386", 600: "#28786d", 700: "#1d5e56" },
      },
      boxShadow: { card: "0 12px 35px rgba(19, 44, 44, .06)" },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
