import type { Config } from "tailwindcss";

// Design tokens (colors, spacing, typography) get centralized here per plan
// §9 as feature stories introduce them. Empty/default at scaffold stage.
const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
