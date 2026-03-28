module.exports = {
  content: [
    "./farmers_dashboard/templates/**/*.html",
    "./veterinary_dashboard/templates/**/*.html",
    "./users/templates/**/*.html",
    "./templates/includes/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        green: "#1F5D3B",
        "green-dark": "#16422a",
        forest: "#1F5D3B",
        cream: "#F5F2E8",
        muted: "#6B7280",
        "vet-navy": "#10345b",
      },
      fontFamily: {
        display: ["Poppins", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
      boxShadow: {
        soft: "0 18px 48px rgba(148,163,184,0.14)",
      },
    },
  },
  plugins: [],
};
