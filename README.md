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

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

Create a `.env` file in `backend/` with your LLM credentials (OpenAI or Gemini):

```
OPENAI_API_KEY=sk-...        # optional
OPENAI_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini
GEMINI_API_KEY=AIza...       # optional
GEMINI_MODEL=gemini-1.5-flash-latest
LLM_PROVIDER=auto            # set to "openai", "gemini", or leave as auto
CORS_ALLOW_ORIGINS=http://localhost:5173
```

If no API key is present, the backend falls back to simulated persona and judge outputs so you can iterate on the UI.

## Next steps

- Replace the simulated responses with real OpenAI calls once credentials are available.
- Enrich persona definitions with uploaded CVs or trait libraries.
- Track debate history and persona memory for longitudinal behavior.
- Expand the judge to produce structured rationales and confidence scores.
