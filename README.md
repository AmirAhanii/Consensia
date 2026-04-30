# Consensia

A research project exploring whether a large language model can act as a trustworthy judge — orchestrating multiple expert roles to reach an explainable consensus.

## Project structure

```
frontend/   # React + Vite + Tailwind prototype UI
backend/    # FastAPI service orchestrating personas and judge consensus
```

## Getting started

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

The app runs on `http://localhost:5173` by default. By **omitting** `VITE_API_BASE_URL`, the UI calls same-origin `/api/...` and Vite proxies to the backend (see `vite.config.ts`). Only add a `.env` entry if the API is on another origin, for example:

```
VITE_API_BASE_URL=https://your-api.example.com
```

If login hangs and the error mentions `http://localhost:8000`, your shell or a `.env` file may still be setting `VITE_API_BASE_URL` — remove it or run `unset VITE_API_BASE_URL` before `npm run dev`. Docker Compose sets `VITE_API_BASE_URL=""` on the frontend service so the proxy is always used there.

### Backend (FastAPI)

**macOS / Linux (Terminal):**

```bash
cd backend
python3 -m venv .venv          # create venv (run once per project)
source .venv/bin/activate      # activate venv
pip install -e .               # or: pip install -r requirements.txt
# if needed: pip install fastapi "uvicorn[standard]"
uvicorn app.main:app --reload --port 8000
```

**Windows (CMD):**

```cmd
cd backend
py -m venv .venv               # create venv (run once per project)
.venv\Scripts\activate         # activate venv
pip install -e .
REM or: pip install -r requirements.txt
REM if needed: pip install fastapi "uvicorn[standard]"
uvicorn app.main:app --reload --port 8000
REM or: py -m uvicorn app.main:app --reload --port 8000
```

Copy `backend/env.template` to `backend/.env` and fill in your local credentials (never commit the real keys):

```
cp backend/env.template backend/.env
```

Update the values as needed, for example:

```
GEMINI_API_KEY=AIza...       # optional
GEMINI_MODEL=gemini-2.0-flash
OPENAI_API_KEY=sk-...        # optional
OPENAI_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini
LLM_PROVIDER=auto            # set to "openai", "gemini", or leave as auto
CORS_ALLOW_ORIGINS=http://localhost:5173
```

If no API key is present, the backend falls back to simulated persona and judge outputs so you can iterate on the UI.

## Docker (recommended)

Use Docker Compose to avoid local dependency/env mismatches. This runs backend + frontend in dev mode.

```bash
docker compose up --build
```

Then open `http://localhost:5173`.

Stop:
```bash
docker compose down
```

Tail logs (optional):
```bash
docker compose logs -f
```

**Database / register errors (`relation "users" does not exist`):** Postgres was empty or migrations had not run. The app runs `alembic upgrade heads` on startup (this repo has two migration heads). To run migrations manually:

```bash
docker compose exec backend alembic upgrade heads
```

If you want to provide real API keys, create `backend/.env` locally (and do not commit it), or pass environment variables in `docker-compose.yml`.

## GitHub Pages (same site as `*.github.io`)

The frontend is set up for **project pages** (`https://<user>.github.io/<repo>/`) or **user/org pages** (repo named `<user>.github.io`, base path `/`).

**Important:** the path in the URL is always the **GitHub repository name**. For example [https://amirahanii.github.io/Consensia-webpage/](https://amirahanii.github.io/Consensia-webpage/) is served from the repo **`amirahanii/Consensia-webpage`**, not from a differently named repo. The build sets `VITE_BASE_PATH` to `/<repo>/` automatically, so that URL only works if this project (including `.github/workflows/deploy-pages.yml` and the `frontend/` folder) lives in **`Consensia-webpage`** and Pages is turned on there. You do not need two separate “sites” in two repos unless you want two URLs.

1. Put this codebase in the repo that matches your desired URL (e.g. merge or push into **`Consensia-webpage`**), then push to `main` (or run **Actions → Deploy GitHub Pages → Run workflow**).
2. In the GitHub repo: **Settings → Pages → Build and deployment → Source: GitHub Actions** (pick the “GitHub Pages” environment the first time it prompts).
3. After the workflow finishes, open the **Pages URL** shown in the run summary. Routes like `/app` work because the build copies `index.html` to `404.html`.

**API from Pages:** set a repository secret `VITE_API_BASE_URL` to your public backend URL (for example `https://api.example.com`). Update backend `CORS_ALLOW_ORIGINS` to include your `https://<user>.github.io` origin.

**Local check with a subpath** (replace with your repo name):  
`cd frontend && VITE_BASE_PATH=/Consensia-webpage/ npm run build:pages && npx vite preview`  
Then open `http://localhost:4173/Consensia-webpage/` (preview serves the built `base` from `dist`).

If you keep developing in a repo named differently from the Pages URL, either **rename** the GitHub repo, or **move the default branch** of `Consensia-webpage` to contain this tree; publishing from `Consensia` alone would give `https://amirahanii.github.io/Consensia/` instead.

## Next steps

- Replace the simulated responses with real OpenAI calls once credentials are available.
- Enrich persona definitions with uploaded CVs or trait libraries.
- Track debate history and persona memory for longitudinal behavior.
- Expand the judge to produce structured rationales and confidence scores.
