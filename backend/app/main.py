from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .schemas import ConsensusRequest, ConsensusResponse
from .services.llm import LLMService


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Placeholder for startup/shutdown tasks (e.g., warm caches, stream managers).
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


@app.on_event("startup")
async def configure() -> None:
    settings = get_settings()
    create_cors(app, settings)


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return LLMService(settings=settings)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


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
            *(service.generate_persona_answer(persona, payload.question) for persona in payload.personas)
        )
        judge_consensus = await service.generate_judge_consensus(persona_answers, payload.question)
    except Exception as exc:  # pragma: no cover - bubble unexpected errors with FastAPI semantics
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Consensus generation failed: {exc}",
        ) from exc

    return ConsensusResponse(personas=list(persona_answers), judge=judge_consensus)

