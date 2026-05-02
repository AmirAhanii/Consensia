import { authHeaders } from "./authHeaders";
import { API_BASE_URL } from "./config";

// Render free tier: cold start + migrations on first request can exceed 60s.
const DEFAULT_TIMEOUT_MS = 180_000;

function resolveApiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!API_BASE_URL) {
    return p;
  }
  return `${API_BASE_URL}${p}`;
}

/**
 * Fetch against the API with a hard timeout so the UI cannot hang forever
 * when the backend is down, blocked by CORS, or the URL points nowhere.
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const url = resolveApiUrl(path);
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const hint = API_BASE_URL
    ? API_BASE_URL
    : [
        "browser calls same-origin /api",
        "Vite must proxy to a running API (default http://127.0.0.1:8000)",
        "Docker Compose sets VITE_DEV_PROXY_TARGET=http://backend:8000 on the frontend service",
        "override with frontend/.env: VITE_DEV_PROXY_TARGET=… or point VITE_API_BASE_URL at the API origin",
      ].join(" · ");
  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error(
        `Request timed out after ${timeoutMs / 1000}s. Is the API reachable? ${hint}`
      );
    }
    if (e instanceof TypeError) {
      throw new Error(
        `Could not reach the API (${hint}). If the UI is on https, do not set VITE_API_BASE_URL to http unless the page is also http. Otherwise start the backend (e.g. uvicorn on :8000 or \`docker compose up\`) and wait until /health responds.`
      );
    }
    throw e;
  } finally {
    window.clearTimeout(timer);
  }
}

/** Same as `apiFetch` but sends the Bearer token (for authenticated routes). */
export async function authApiFetch(
  path: string,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const headers = new Headers(init.headers ?? undefined);
  const auth = authHeaders();
  if (auth.Authorization) {
    headers.set("Authorization", auth.Authorization);
  }
  return apiFetch(
    path,
    {
      ...init,
      headers,
    },
    timeoutMs
  );
}

/** `response.json()` is not covered by the fetch AbortSignal once headers arrive — cap it too. */
export async function readResponseJson<T>(
  response: Response,
  timeoutMs: number = 15_000
): Promise<T> {
  return Promise.race([
    response.json() as Promise<T>,
    new Promise<T>((_, reject) =>
      setTimeout(
        () =>
          reject(
            new Error(
              "Reading the API response timed out (incomplete or very slow body)."
            )
          ),
        timeoutMs
      )
    ),
  ]);
}
