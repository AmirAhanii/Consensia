import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {}
  },
  plugins: [
    plugin(({ addVariant }) => {
      addVariant("light", 'html[data-theme="light"] &');
    }),
  ],
};

export default config;

