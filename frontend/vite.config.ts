import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Containers usually don't have a GUI / xdg-open available.
    // Auto-open locally only when explicitly enabled.
    open: process.env.VITE_OPEN === "true",
  }
});

