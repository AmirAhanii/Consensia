/**
 * - **Unset / empty** → same-origin `/api/...` (Vite `server.proxy` / `preview.proxy` in dev, or UI+API on one host).
 * - **Set** `VITE_API_BASE_URL` to a full origin only when the API is on another host (e.g. static site + public API).
 *
 * Note: Vite reads `VITE_*` from the shell that starts `npm run dev`. If you still see calls to
 * `http://localhost:8000`, run `unset VITE_API_BASE_URL` or remove it from `.env*`.
 */
const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined;

function trimSlash(s: string): string {
  return s.replace(/\/+$/, "");
}

export const API_BASE_URL: string = (() => {
  if (fromEnv === undefined || fromEnv === null) {
    return "";
  }
  const trimmed = String(fromEnv).trim();
  if (trimmed === "") {
    return "";
  }
  return trimSlash(trimmed);
})();

/** Must match API `MAX_PERSONA_LIMIT` (use `VITE_MAX_PERSONA_LIMIT` in frontend `.env` if you change it). */
export const MAX_DEBATERS_PER_SESSION: number = (() => {
  const raw = import.meta.env.VITE_MAX_PERSONA_LIMIT as string | undefined;
  const n = raw !== undefined && raw !== null ? Number.parseInt(String(raw).trim(), 10) : Number.NaN;
  if (!Number.isFinite(n) || n < 1) return 5;
  return Math.min(50, n);
})();

/** Total attachment payload cap for `/api/debate` (must match backend / product copy). */
export const MAX_DEBATE_ATTACHMENT_TOTAL_BYTES = 12 * 1024 * 1024;

