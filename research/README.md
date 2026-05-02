# Research workspace

Experiments that are **not** wired into the main Consensia app — e.g. tangled-commit labeling, persona vs baseline, and **which LLM** you use for annotation.

## Hypothesis you mentioned

**Gemini Flash** can degrade when the system prompt is huge (full persona JSON + long protocol), while **OpenAI reasoning models** (`o3-mini`, `o4-mini`, etc.) may stay more stable because internal reasoning is separated from the final answer — worth measuring, not assuming.

## Setup

```bash
cd research
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — set OPENAI_API_KEY and optionally OPENAI_REASONING_MODEL
```

## Smoke test (reasoning + JSON)

Runs a tiny synthetic diff and asks for strict JSON labels (prints usage + output):

```bash
python scripts/openai_reasoning_smoke.py
```

Next steps (same folder): copy prompt patterns from `scrapingv2/backend/data/testing-annotation/testall/run_annotation_batch.py`, swap the Gemini client for `OpenAI().chat.completions.create`, keep **short** persona text + **anchored** labels, then compare metrics to your Gemini baseline on the same hunks.
