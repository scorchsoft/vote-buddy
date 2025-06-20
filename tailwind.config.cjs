module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        bp: {
          blue:  "#002D59",
          "blue-light": "#1a4a7a",
          red:   "#DC0714",
          "red-light": "#e73744",
          "red-dark": "#b90510",
          yellow:"#FFEB3B",
          grey: {
            50:  "#F8FAFC",
            100: "#F1F5F9",
            200: "#E2E8F0",
            300: "#CBD5E1",
            400: "#94A3B8",
            500: "#64748B",
            600: "#475569",
            700: "#334155",
            800: "#1E293B",
            900: "#0F172A",
          },
        },
      },
      fontFamily: {
        sans: ['Gotham', 'Arial', 'Helvetica Neue', 'sans-serif'],
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
