/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        canvas: "#F5F6F3",
        ink: "#18352D",
        muted: "#74827C",
        line: "#E5E9E3",
        forest: "#23664D",
        "forest-dark": "#163E30",
        mint: "#EAF2E9",
        sidebar: "#132D25",
        sand: "#F4ECDD",
        ochre: "#9F632D",
      },
      borderRadius: { card: "18px" },
    },
  },
  plugins: [],
};
