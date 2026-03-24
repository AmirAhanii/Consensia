import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env from the backend directory, not the current working directory
# This ensures cross-platform compatibility
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)


def resolve_research_raw_authors_dir() -> Path:
    """
    Directory for frozen *_raw.json snapshots (Scholar scraper output).
    Override with RESEARCH_RAW_AUTHORS_DIR for Docker/custom layouts.
    """
    override = (os.getenv("RESEARCH_RAW_AUTHORS_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (backend_dir / "data" / "raw_authors").resolve()


class Settings(BaseModel):
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "auto").strip())
    openai_api_key: str | None = Field(
        default_factory=lambda: (os.getenv("OPENAI_API_KEY") or "").strip() or None
    )
    # Optional for OpenAI-compatible / Azure-compatible endpoints.
    # If unset, the OpenAI SDK uses its default base URL.
    openai_base_url: str | None = Field(
        default_factory=lambda: (os.getenv("OPENAI_BASE_URL") or "").strip() or None
    )
    # Required for Azure OpenAI.
    openai_api_version: str | None = Field(
        default_factory=lambda: (os.getenv("OPENAI_API_VERSION") or "").strip() or None
    )
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip())
    judge_model: str = Field(default_factory=lambda: os.getenv("JUDGE_MODEL", "gpt-4o-mini").strip())
    gemini_api_key: str | None = Field(
        default_factory=lambda: (os.getenv("GEMINI_API_KEY") or "").strip() or None
    )
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")) # "gemini-2.0-flash"
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")
    )

    # Token/cost guardrails (to avoid large spend per request)
    max_personas_per_request: int = Field(
        default_factory=lambda: int(os.getenv("MAX_PERSONAS_PER_REQUEST", "4"))
    )
    max_output_tokens_persona: int = Field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS_PERSONA", "180"))
    )
    max_output_tokens_judge: int = Field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS_JUDGE", "220"))
    )
    # When building the judge prompt, truncate each persona answer to reduce input tokens.
    judge_context_max_chars_per_persona: int = Field(
        default_factory=lambda: int(os.getenv("JUDGE_CONTEXT_MAX_CHARS_PER_PERSONA", "900"))
    )
    # CV->persona prompt can get huge; cap extracted text to limit input tokens.
    cv_prompt_max_chars: int = Field(
        default_factory=lambda: int(os.getenv("CV_PROMPT_MAX_CHARS", "12000"))
    )
    cv_prompt_max_output_tokens: int = Field(
        default_factory=lambda: int(os.getenv("CV_PROMPT_MAX_OUTPUT_TOKENS", "300"))
    )
    research_prompt_max_chars: int = Field(
        default_factory=lambda: int(os.getenv("RESEARCH_PROMPT_MAX_CHARS", "14000"))
    )
    research_prompt_max_output_tokens: int = Field(
        default_factory=lambda: int(os.getenv("RESEARCH_PROMPT_MAX_OUTPUT_TOKENS", "320"))
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

