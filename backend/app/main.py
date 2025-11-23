from __future__ import annotations

import asyncio
import io
import json
from contextlib import asynccontextmanager

import pdfplumber
from docx import Document
from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .schemas import ConsensusRequest, ConsensusResponse
from .services.llm import LLMService, Provider


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Consensia API",
    version="0.1.0",
    description="Backend service orchestrating multi-persona LLM discussions with a judge consensus.",
    lifespan=lifespan,
)


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
) -> ConsensusResponse:
    if not payload.personas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one persona is required.",
        )

    try:
        persona_answers = await asyncio.gather(
            *(service.generate_persona_answer(persona, payload.question)
              for persona in payload.personas)
        )
        judge_consensus = await service.generate_judge_consensus(persona_answers, payload.question)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Consensus generation failed: {exc}",
        ) from exc

    return ConsensusResponse(
        personas=list(persona_answers),
        judge=judge_consensus
    )


# ------------------------------------------------------------------------------------
# NEW: CV -> PERSONA ENDPOINT
# ------------------------------------------------------------------------------------
@app.post("/api/persona/from-cv")
async def extract_persona_from_cv(
    file: UploadFile = File(...),
    service: LLMService = Depends(get_llm_service),
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

    # Prompt
    prompt = f"""
You are an expert at analyzing CVs and converting them into structured persona profiles
for use inside an AI multi-agent system.

Analyze the CV below and extract:

1. The candidate's full name.
2. Their most appropriate job title (short, e.g., "Software Engineer", "Full-Stack Developer").
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
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.parsed

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
