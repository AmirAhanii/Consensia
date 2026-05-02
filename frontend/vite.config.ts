import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

/** GitHub project pages use `/RepoName/`; user site `username.github.io` uses `/`. */
function appBase(): string {
  const raw = (process.env.VITE_BASE_PATH ?? "/").trim();
  if (!raw || raw === "/") return "/";
  const withSlash = raw.startsWith("/") ? raw : `/${raw}`;
  return withSlash.endsWith("/") ? withSlash : `${withSlash}/`;
}

export default defineConfig(({ mode }) => {
  // `.env` / `.env.local` are not on `process.env` unless loaded — required for `VITE_DEV_PROXY_TARGET`
  // when you run `npm run dev` from `frontend/` with a local `.env` file.
  const fileEnv = loadEnv(mode, process.cwd(), "VITE_");
  const devProxyTarget = (
    fileEnv.VITE_DEV_PROXY_TARGET ||
    process.env.VITE_DEV_PROXY_TARGET ||
    "http://127.0.0.1:8000"
  ).trim();

  const apiProxy = {
    "/api": {
      target: devProxyTarget,
      changeOrigin: true,
    },
  };

  return {
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
  };
});

