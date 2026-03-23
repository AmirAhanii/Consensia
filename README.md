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

The app runs on `http://localhost:5173` by default. Configure the API target via `.env`:

```
VITE_API_BASE_URL=http://localhost:8000
```

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

If you want to provide real API keys, create `backend/.env` locally (and do not commit it), or pass environment variables in `docker-compose.yml`.

## Next steps

- Replace the simulated responses with real OpenAI calls once credentials are available.
- Enrich persona definitions with uploaded CVs or trait libraries.
- Track debate history and persona memory for longitudinal behavior.
- Expand the judge to produce structured rationales and confidence scores.
