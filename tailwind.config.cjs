module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        bp: {
          blue:  "#002D59",
          red:   "#DC0714",
          yellow:"#FFEB3B",
          gray: {
            50:  "#F7F7F9",
            700: "#3F4854",
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
