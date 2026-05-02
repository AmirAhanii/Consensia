# Put Consensia on a free public URL (`consensia.*`)

You do **not** need a paid `.com`. Common free patterns:

| Host | Example URL | Notes |
|------|----------------|-------|
| **Netlify** | `https://consensia.netlify.app` | Pick site name `consensia` if free. Repo includes `netlify.toml`. |
| **Cloudflare Pages** | `https://consensia.pages.dev` | Or a `*.workers.dev` / custom later. |
| **Vercel** | `https://consensia.vercel.app` | New project → import repo → root `frontend`, build `vite build` with `VITE_BASE_PATH=/`. |
| **GitHub Pages** | `https://YOU.github.io/REPO/` | Already wired via `.github/workflows/deploy-pages.yml`; `consensia` appears in path if repo is named `Consensia`. |

The **frontend** is static. The **API** must be reachable over HTTPS on another URL unless you use a serverless proxy (advanced).

---

## 1) Frontend on Netlify (recommended for `consensia.netlify.app`)

1. Push this repo to GitHub.
2. [Netlify](https://www.netlify.com/) → **Add new site** → **Import an existing project** → pick the repo.
3. Netlify should read **`netlify.toml`** (build base `frontend`, publish `dist`).
4. **Site settings → Domain management → Options** → set site name to **`consensia`** (or another free slug). URL becomes `https://consensia.netlify.app`.
5. **Site settings → Environment variables**:
   - `VITE_API_BASE_URL` = your public API origin, e.g. `https://consensia-api.onrender.com` (no trailing slash).
   - Keep `VITE_BASE_PATH` unset or `/` for this subdomain (already in `netlify.toml` command).
6. Trigger **Deploy site**.

**Local sanity check (root URL, no subpath):**

```bash
cd frontend
VITE_BASE_PATH=/ VITE_API_BASE_URL=https://your-api.example.com npm run build:pages
npx vite preview
```

---

## 2) Backend API (must be HTTPS for browsers)

Free tiers that work well with FastAPI + Postgres:

- **Render** — Web Service + managed Postgres free tier (cold starts; fine for demos).
- **Fly.io** — Small VM + Fly Postgres.
- **Railway** — Often has trial credit.

Set on the API host:

- `CORS_ALLOW_ORIGINS` — include your real site origin, e.g. `https://consensia.netlify.app` (and `http://localhost:5173` only if you still dev locally).
- `FRONTEND_BASE_URL` — same public UI URL (if your app uses it for emails/links).

Then set **`VITE_API_BASE_URL`** on the static host to that API origin.

---

## 3) GitHub Pages (already in repo)

See root **README.md** → “GitHub Pages”. URL is always `https://<user>.github.io/<repo>/`. To get “consensia” in the path, name the repo **`Consensia`** (case-insensitive path segment). Custom apex domains on Pages are optional and can be free later (DNS).

---

## Checklist

- [ ] UI builds with `VITE_BASE_PATH=/` when using `*.netlify.app` / `*.vercel.app`.
- [ ] `VITE_API_BASE_URL` points at a **live** HTTPS API.
- [ ] API `CORS_ALLOW_ORIGINS` includes the **exact** UI origin (scheme + host, no path).
- [ ] API secrets (OpenAI, DB, JWT) set only on the server, never in the frontend bundle.
