# Consensia Backend

FastAPI service that orchestrates persona-level responses and a judge consensus for the Consensia project.

## Getting started

```bash
# Create and activate a virtual environment (example with uv)
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt  # or `uv pip install .`
```

Alternatively, using pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Environment variables

Create a `.env` file in the `backend/` directory and set:

```
# Option A: OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini

# Option B: Gemini (free tier)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash-latest

# Optional: force provider selection ("openai", "gemini", or leave unset for auto)
LLM_PROVIDER=auto

# Shared config
CORS_ALLOW_ORIGINS=http://localhost:5173
```

### Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs.

