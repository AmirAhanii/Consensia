import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "auto"))
    openai_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    judge_model: str = Field(default_factory=lambda: os.getenv("JUDGE_MODEL", "gpt-4o-mini"))
    gemini_api_key: str | None = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest"))
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

