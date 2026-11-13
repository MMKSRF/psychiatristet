/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#3d0713",
        muted: "#75666a",
        canvas: "#ffffff",
        teal: {
          50: "#fffaf1",
          100: "#fff3dc",
          300: "#ffbe56",
          400: "#e8a73c",
          500: "#650217",
          600: "#650217",
          700: "#4d0112",
          800: "#3d0713",
          900: "#2b000a",
          950: "#210008",
        },
      },
      boxShadow: { card: "0 12px 35px rgba(61, 7, 19, .06)" },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
