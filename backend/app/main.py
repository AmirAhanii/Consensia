from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from .auth.router import router as auth_router

import pdfplumber
from docx import Document
from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings, resolve_research_raw_authors_dir
from .schemas import ConsensusRequest, ConsensusResponse, JudgeConsensus, TokenUsage
from .services.llm import LLMService, Provider


_APP_DIR = Path(__file__).resolve().parent
# Shipped snapshots (always present with the code; survives empty Docker data volume mounts).
_BUNDLED_RAW_AUTHORS_DIR = _APP_DIR / "bundled_raw_authors"


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield



app = FastAPI(
    title="Consensia API",
    version="0.1.0",
    description="Backend service orchestrating multi-persona LLM discussions with a judge consensus.",
    lifespan=lifespan,
)

app.include_router(auth_router)

logger = logging.getLogger(__name__)


def create_cors(app_: FastAPI, settings: Settings) -> None:
    app_.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


create_cors(app, get_settings())


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return LLMService(settings=settings)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ------------------------------------------------------------------------------------
# CONSENSUS ENDPOINT (needs to stay above CV endpoint)
# ------------------------------------------------------------------------------------
@app.post(
    "/api/consensus",
    response_model=ConsensusResponse,
    tags=["consensus"],
    summary="Generate persona answers and judge consensus",
)
async def generate_consensus(
    payload: ConsensusRequest,
    service: LLMService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
) -> ConsensusResponse:
    if not payload.personas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one persona is required.",
        )

    if len(payload.personas) > settings.max_personas_per_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Too many personas in one request. "
                f"Max is {settings.max_personas_per_request}."
            ),
        )

    try:
        persona_answers = await asyncio.gather(
            *(service.generate_persona_answer(persona, payload.question)
              for persona in payload.personas)
        )
        if len(persona_answers) == 1:
            # Cost optimization: in single-persona research mode, avoid an extra LLM judge call.
            # Reuse the persona answer as consensus and provide local reasoning text.
            only = persona_answers[0]
            judge_consensus = JudgeConsensus(
                summary=only.answer,
                reasoning=(
                    "Single-persona mode: consensus is derived directly from the "
                    "persona response without running a separate judge model."
                ),
                usage=None,
            )
        else:
            judge_consensus = await service.generate_judge_consensus(persona_answers, payload.question)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Consensus generation failed: {exc}",
        ) from exc

    total_usage: TokenUsage | None = None
    if judge_consensus.usage or any((p.usage is not None) for p in persona_answers):
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        for p in persona_answers:
            if p.usage:
                prompt_tokens += p.usage.prompt_tokens
                completion_tokens += p.usage.completion_tokens
                total_tokens += p.usage.total_tokens
        if judge_consensus.usage:
            prompt_tokens += judge_consensus.usage.prompt_tokens
            completion_tokens += judge_consensus.usage.completion_tokens
            total_tokens += judge_consensus.usage.total_tokens
        total_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    return ConsensusResponse(
        personas=list(persona_answers),
        judge=judge_consensus,
        usage=total_usage,
    )


# ------------------------------------------------------------------------------------
# NEW: CV -> PERSONA ENDPOINT
# ------------------------------------------------------------------------------------
@app.post("/api/persona/from-cv")
async def extract_persona_from_cv(
    file: UploadFile = File(...),
    service: LLMService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
):
    import json

    content = await file.read()
    text = ""

    # PDF
    if file.filename.endswith(".pdf"):
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception:
            raise HTTPException(400, "Failed to read PDF file")

    # DOCX
    elif file.filename.endswith(".docx"):
        try:
            doc = Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            raise HTTPException(400, "Failed to read DOCX file")
    else:
        raise HTTPException(400, "Only PDF and DOCX files supported")

    if not text.strip():
        raise HTTPException(400, "CV appears empty")

    # CV prompts can get huge; cap extracted text to avoid big input token costs.
    if len(text) > settings.cv_prompt_max_chars:
        text = text[: settings.cv_prompt_max_chars].rstrip() + "\n...[truncated]"

    # Prompt
    prompt = f"""
You are an expert at analyzing CVs and converting them into structured persona profiles
for use inside an AI multi-agent system.

Analyze the CV below and extract:

1. The candidate's full name.
2. Their most appropriate job title (short, e.g., "Software Engineer(candidate's name)", "Full-Stack Developer(candidate's name)").
3. A persona-style description (2–4 sentences) summarizing:
   - technical strengths,
   - experience level,
   - primary focus areas,
   - reasoning style,
   - typical priorities when solving problems.

IMPORTANT RULES:
- Do NOT output anything except VALID JSON.
- Do NOT include raw CV text.
- Do NOT write “here is the CV” or anything similar.
- Description must sound like a persona background, NOT a resume.
- Keep it concise but informative.

Return ONLY this JSON:

{{
  "name": "",
  "title": "",
  "description": ""
}}

CV CONTENT:
{text}
"""

    # OpenAI
    if service._provider == Provider.OPENAI and service._openai_client:
        response = await service._openai_client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=settings.cv_prompt_max_output_tokens,
        )
        message = response.choices[0].message
        parsed_message = getattr(message, "parsed", None)
        if parsed_message and isinstance(parsed_message, dict):
            return parsed_message

        raw = (message.content or "").strip()
        try:
            return json.loads(raw)
        except Exception:
            raise HTTPException(
                500,
                f"OpenAI returned invalid JSON for CV extraction: {raw[:200]}"
            )

    # Gemini 
    elif service._provider == Provider.GEMINI and service._gemini_model:
        result = await asyncio.to_thread(
            service._gemini_model.generate_content,
            [{"role": "user", "parts": [prompt]}],
        )

        raw = (result.text or "").strip()

        # Clean markdown fences
        if raw.startswith("```"):
            raw = raw.strip("`\n ")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        try:
            return json.loads(raw)
        except Exception:
            raise HTTPException(
                500,
                f"Gemini returned invalid JSON: {raw[:200]}"
            )

    else:
        raise HTTPException(500, "No LLM provider configured")


def _compact_research_author(raw_author: dict[str, Any]) -> dict[str, Any]:
    papers = raw_author.get("papers", []) if isinstance(raw_author, dict) else []
    compact_papers: list[dict[str, Any]] = []

    for p in papers[:25]:
        if not isinstance(p, dict):
            continue
        compact_papers.append(
            {
                "title": p.get("title"),
                "year": p.get("year"),
                "venue": p.get("venue"),
                "authors": p.get("authors"),
                "citation_count": p.get("citation_count"),
                "snippet": p.get("snippet"),
                "abstract": p.get("abstract"),
                # Some pipelines include intro text under different keys.
                "introduction": p.get("introduction") or p.get("intro"),
            }
        )

    return {
        "name": raw_author.get("name"),
        "scholar_id": raw_author.get("scholar_id"),
        "affiliation": raw_author.get("affiliation"),
        "profile_url": raw_author.get("profile_url"),
        "papers": compact_papers,
    }


def _research_snapshot_preview(raw_author: dict[str, Any], max_len: int = 120) -> str | None:
    """Short line for persona-style cards in the UI (not raw JSON)."""
    papers = raw_author.get("papers")
    if not isinstance(papers, list):
        return None
    for p in papers:
        if not isinstance(p, dict):
            continue
        for key in ("abstract", "snippet", "title"):
            text = p.get(key)
            if isinstance(text, str):
                s = " ".join(text.split())
                if len(s) < 20:
                    continue
                if len(s) > max_len:
                    cut = s[: max_len - 1].rsplit(" ", 1)[0]
                    return cut + "…"
                return s
    return None


def _heuristic_research_persona(raw_author: dict[str, Any]) -> dict[str, Any]:
    """
    Build {name, title, description} without an LLM (demo / no API key / provider none).
    """
    name = (raw_author.get("name") or "Researcher").strip() or "Researcher"
    aff = (raw_author.get("affiliation") or "").strip()
    papers = raw_author.get("papers")
    titles: list[str] = []
    if isinstance(papers, list):
        for p in papers[:8]:
            if isinstance(p, dict):
                t = p.get("title")
                if isinstance(t, str) and t.strip():
                    titles.append(t.strip())
    topic = ""
    if titles:
        topic = " Representative themes include: " + "; ".join(titles[:3])
        if len(titles) > 3:
            topic += "…"
    description = (
        (f"Based at {aff}. " if aff else "")
        + (topic + " " if topic else "")
        + "They reason from empirical software engineering evidence and prioritize rigor, replication, and practical impact."
    ).strip()
    if len(description) > 2400:
        description = description[:2397] + "…"
    return {
        "name": name,
        "title": f"Software Engineering Researcher ({name})",
        "description": description,
    }


_SCHOLAR_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def resolve_research_snapshot_path(scholar_id: str) -> Path | None:
    """Prefer configured data dir, then bundled app copies (Docker volume-safe)."""
    if not _SCHOLAR_ID_RE.fullmatch(scholar_id):
        return None
    fname = f"{scholar_id}_raw.json"
    primary = resolve_research_raw_authors_dir() / fname
    if primary.is_file():
        return primary
    bundled = _BUNDLED_RAW_AUTHORS_DIR / fname
    if bundled.is_file():
        return bundled
    return None


def collect_research_snapshot_rows() -> list[dict[str, Any]]:
    """Merge snapshots from data dir and bundled dir (dedupe by scholar_id)."""
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    dirs: list[Path] = [resolve_research_raw_authors_dir(), _BUNDLED_RAW_AUTHORS_DIR]
    for d in dirs:
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*_raw.json")):
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                logger.debug("Skip unreadable snapshot %s: %s", path, exc)
                continue
            if not isinstance(data, dict):
                continue
            sid = data.get("scholar_id") or path.stem.replace("_raw", "")
            if sid in seen:
                continue
            seen.add(sid)
            rows.append(
                {
                    "scholar_id": sid,
                    "name": data.get("name"),
                    "affiliation": data.get("affiliation"),
                    "preview": _research_snapshot_preview(data),
                    "filename": path.name,
                }
            )
    return sorted(rows, key=lambda r: ((r.get("name") or "").lower(), r.get("scholar_id") or ""))


async def _persona_from_research_author_dict(
    raw_author: dict[str, Any],
    service: LLMService,
    settings: Settings,
) -> dict[str, Any]:
    compact = _compact_research_author(raw_author)
    compact_json = json.dumps(compact, ensure_ascii=False)
    if len(compact_json) > settings.research_prompt_max_chars:
        compact_json = compact_json[: settings.research_prompt_max_chars].rstrip() + "\n...[truncated]"

    prompt = f"""
You are an expert in Software Engineering researcher profiling.
Given structured researcher metadata and publication evidence, generate a practical persona
for a software-engineering discussion simulator.

Extract and return ONLY valid JSON with:
{{
  "name": "",
  "title": "",
  "description": ""
}}

Requirements:
- name: readable researcher name.
- title: short role title tied to the person, e.g. "Software Engineering Researcher (Name)".
- description: 2-4 sentences about expertise areas, methodological tendencies,
  reasoning style, and practical priorities in software engineering decisions.
- Ground claims in provided evidence (papers/abstracts/snippets).
- Do NOT include raw paper dumps or extra keys.

RESEARCH EVIDENCE:
{compact_json}
"""

    if service._provider == Provider.OPENAI and service._openai_client:
        response = await service._openai_client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=settings.research_prompt_max_output_tokens,
        )
        message = response.choices[0].message
        parsed_message = getattr(message, "parsed", None)
        if parsed_message and isinstance(parsed_message, dict):
            return parsed_message

        raw = (message.content or "").strip()
        try:
            return json.loads(raw)
        except Exception:
            raise HTTPException(
                500,
                f"OpenAI returned invalid JSON for research persona extraction: {raw[:200]}"
            )

    if service._provider == Provider.GEMINI and service._gemini_model:
        result = await asyncio.to_thread(
            service._gemini_model.generate_content,
            [{"role": "user", "parts": [prompt]}],
        )

        raw = (result.text or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`\n ")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        try:
            return json.loads(raw)
        except Exception:
            raise HTTPException(
                500,
                f"Gemini returned invalid JSON for research persona extraction: {raw[:200]}"
            )

    return _heuristic_research_persona(raw_author)


@app.get("/api/research/raw-authors")
async def list_research_raw_authors() -> list[dict[str, Any]]:
    """List Scholar snapshots from data/raw_authors and app/bundled_raw_authors (*_raw.json)."""
    d = resolve_research_raw_authors_dir()
    if not d.is_dir():
        if d.parent.is_dir():
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
    return collect_research_snapshot_rows()


@app.post("/api/persona/from-research-snapshot/{scholar_id}")
async def persona_from_research_snapshot(
    scholar_id: str,
    service: LLMService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Build persona from a saved file: data/raw_authors/{scholar_id}_raw.json"""
    if not _SCHOLAR_ID_RE.fullmatch(scholar_id):
        raise HTTPException(400, "Invalid scholar_id")

    path = resolve_research_snapshot_path(scholar_id)
    if path is None:
        raise HTTPException(404, f"No snapshot for scholar_id={scholar_id}")

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_author = json.load(f)
    except Exception as exc:
        raise HTTPException(400, f"Invalid JSON snapshot: {exc}") from exc

    if not isinstance(raw_author, dict):
        raise HTTPException(400, "Snapshot root must be an object")

    return await _persona_from_research_author_dict(raw_author, service, settings)


@app.post("/api/persona/from-research-json")
async def extract_persona_from_research_json(
    file: UploadFile = File(...),
    service: LLMService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
):
    """
    Third persona creation path:
    - Accepts a raw author JSON like scraper output (Google Scholar/profile/papers).
    - Returns a frontend-compatible persona payload: {name, title, description}.
    """
    content = await file.read()
    try:
        raw_author = json.loads(content.decode("utf-8"))
    except Exception:
        raise HTTPException(400, "Invalid JSON file")

    if not isinstance(raw_author, dict):
        raise HTTPException(400, "JSON root must be an object")

    return await _persona_from_research_author_dict(raw_author, service, settings)
