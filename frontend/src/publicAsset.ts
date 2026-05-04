/** Join a `public/` path (no leading slash) with Vite `base` for GitHub Pages subpaths. */
export function publicAsset(relativePath: string): string {
  const base = import.meta.env.BASE_URL;
  const path = relativePath.replace(/^\//, "");
  return `${base}${path}`;
}

/** Absolute URL to a `public/` file (use for `<a href>` so paths are never resolved against `/login` etc.). */
export function publicAssetUrl(relativePath: string): string {
  const raw = publicAsset(relativePath);
  if (typeof window === "undefined") {
    return raw;
  }
  try {
    return new URL(raw, window.location.origin).href;
  } catch {
    const path = raw.startsWith("/") ? raw : `/${raw}`;
    return `${window.location.origin}${path}`;
  }
}
