/** Join a `public/` path (no leading slash) with Vite `base` for GitHub Pages subpaths. */
export function publicAsset(relativePath: string): string {
  const base = import.meta.env.BASE_URL;
  const path = relativePath.replace(/^\//, "");
  return `${base}${path}`;
}
