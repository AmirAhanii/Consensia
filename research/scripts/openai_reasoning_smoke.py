"""
Smoke test: OpenAI reasoning model + JSON output on a tiny tangled-commit-style diff.

Usage (from repo root or research/):
  cd research && source .venv/bin/activate && python scripts/openai_reasoning_smoke.py

Requires OPENAI_API_KEY. Optional: OPENAI_REASONING_MODEL, OPENAI_REASONING_EFFORT in research/.env
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def main() -> None:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        print("Set OPENAI_API_KEY in research/.env (see .env.example).", file=sys.stderr)
        sys.exit(1)

    model = (os.getenv("OPENAI_REASONING_MODEL") or "o3-mini").strip()
    effort = (os.getenv("OPENAI_REASONING_EFFORT") or "medium").strip().lower()

    client = OpenAI(api_key=api_key)

    # Minimal diff: mixed bugfix + refactor noise (like tangled commits).
    user_block = """
Classify each CHANGED line index (0-based) into bugfix vs refactoring vs other.

DIFF (changed lines only numbered):
Line 0: -if (x < 0) return -1;
Line 1: +if (x < 0) return handleBadInput(x);
Line 2: -// TODO: clean up
Line 3: +/** Validates input before use */
Line 4: -void foo(){}
Line 5: +void foo(){ bar(); }

Return JSON ONLY with this shape:
{"bugfix":[...],"refactoring":[...],"other":[...]}
Each value is a list of line indices. Every changed line (0..5) must appear in exactly one list.
"""

    system = (
        "You are an expert software engineer annotating tangled commits. "
        "Think step by step, then output valid JSON only (no markdown fences)."
    )

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_block.strip()},
        ],
        "response_format": {"type": "json_object"},
        "max_completion_tokens": 4096,
    }

    # Newer OpenAI reasoning models accept reasoning_effort on chat.completions.
    try_create = lambda extra: client.chat.completions.create(**{**kwargs, **extra})

    response = None
    try:
        response = try_create({"reasoning_effort": effort})
    except TypeError:
        response = try_create({})
    except APIStatusError as e:
        msg = str(e).lower()
        if "reasoning" in msg or "unsupported" in msg or "unknown" in msg:
            response = try_create({})
        else:
            raise

    text = (response.choices[0].message.content or "").strip()
    print("--- model ---")
    print(model)
    print("--- usage ---")
    print(response.usage)
    print("--- raw ---")
    print(text)
    print("--- parsed ---")
    try:
        obj = json.loads(text)
        print(json.dumps(obj, indent=2))
    except json.JSONDecodeError:
        print("(not valid JSON)")


if __name__ == "__main__":
    main()
