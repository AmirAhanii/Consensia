import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** GitHub project pages use `/RepoName/`; user site `username.github.io` uses `/`. */
function appBase(): string {
  const raw = (process.env.VITE_BASE_PATH ?? "/").trim();
  if (!raw || raw === "/") return "/";
  const withSlash = raw.startsWith("/") ? raw : `/${raw}`;
  return withSlash.endsWith("/") ? withSlash : `${withSlash}/`;
}

const devProxyTarget =
  process.env.VITE_DEV_PROXY_TARGET?.trim() || "http://127.0.0.1:8000";

const apiProxy = {
  "/api": {
    target: devProxyTarget,
    changeOrigin: true,
  },
};

export default defineConfig({
  base: appBase(),
  plugins: [react()],
  server: {
    port: 5173,
    // Containers usually don't have a GUI / xdg-open available.
    // Auto-open locally only when explicitly enabled.
    open: process.env.VITE_OPEN === "true",
    // Browser calls same-origin `/api/*`; Vite forwards to the API (avoids CORS in dev).
    proxy: apiProxy,
  },
  preview: {
    port: 4173,
    proxy: apiProxy,
  },
});

