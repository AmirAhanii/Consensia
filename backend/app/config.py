import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)


def _admin_emails_from_env() -> frozenset[str]:
    raw = (os.getenv("ADMIN_EMAILS") or "").strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def resolve_research_raw_authors_dir() -> Path:
    override = (os.getenv("RESEARCH_RAW_AUTHORS_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (backend_dir / "data" / "raw_authors").resolve()


class Settings(BaseModel):
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "auto").strip())
    openai_api_key: str | None = Field(
        default_factory=lambda: (os.getenv("OPENAI_API_KEY") or "").strip() or None
    )
    openai_base_url: str | None = Field(
        default_factory=lambda: (os.getenv("OPENAI_BASE_URL") or "").strip() or None
    )
    openai_api_version: str | None = Field(
        default_factory=lambda: (os.getenv("OPENAI_API_VERSION") or "").strip() or None
    )
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip())
    judge_model: str = Field(default_factory=lambda: os.getenv("JUDGE_MODEL", "gpt-4o-mini").strip())
    gemini_api_key: str | None = Field(
        default_factory=lambda: (os.getenv("GEMINI_API_KEY") or "").strip() or None
    )
    serpapi_api_key: str | None = Field(
        default_factory=lambda: (os.getenv("SERPAPI_API_KEY") or "").strip() or None
    )
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest"))
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")
    )

    frontend_base_url: str = Field(
        default_factory=lambda: os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").strip()
    )
    smtp_host: str = Field(
        default_factory=lambda: os.getenv("SMTP_HOST", "").strip()
    )
    smtp_port: int = Field(
        default_factory=lambda: int(os.getenv("SMTP_PORT", "587"))
    )
    smtp_user: str = Field(
        default_factory=lambda: os.getenv("SMTP_USER", "").strip()
    )
    smtp_password: str = Field(
        default_factory=lambda: os.getenv("SMTP_PASSWORD", "").strip()
    )
    mail_from: str = Field(
        default_factory=lambda: os.getenv("MAIL_FROM", "").strip()
    )

    max_output_tokens_persona: int = Field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS_PERSONA", "180"))
    )
    max_output_tokens_judge: int = Field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS_JUDGE", "220"))
    )
    judge_context_max_chars_per_persona: int = Field(
        default_factory=lambda: int(os.getenv("JUDGE_CONTEXT_MAX_CHARS_PER_PERSONA", "900"))
    )
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
    max_personas_per_session: int = Field(
        default_factory=lambda: max(
            1,
            min(50, int(os.getenv("MAX_PERSONA_LIMIT", "5").strip() or "5")),
        ),
        description="Max personas per debate/consensus request (from MAX_PERSONA_LIMIT env, clamped 1–50).",
    )
    jwt_secret: str = Field(
    default_factory=lambda: os.getenv("JWT_SECRET", "").strip()
    )
    access_token_expire_minutes: int = Field(
    default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )
    google_client_id: str | None = Field(
    default_factory=lambda: (os.getenv("GOOGLE_CLIENT_ID") or "").strip() or None
    )
    admin_emails: frozenset[str] = Field(
        default_factory=_admin_emails_from_env,
        description="Comma-separated ADMIN_EMAILS; those users are promoted to is_admin on startup and login.",
    )
    user_daily_debate_limit: int = Field(
        default_factory=lambda: max(
            1,
            int((os.getenv("USER_DAILY_DEBATE_LIMIT") or "10").strip() or "10"),
        ),
        description="Max /api/debate runs per UTC day for signed-in non-admin users.",
    )
    anon_daily_debate_limit: int = Field(
        default_factory=lambda: max(
            1,
            int((os.getenv("ANON_DAILY_DEBATE_LIMIT") or "5").strip() or "5"),
        ),
        description="Max /api/debate runs per UTC day for guests (no auth).",
    )
    debate_recent_window_messages: int = Field(
        default_factory=lambda: max(
            4,
            min(60, int((os.getenv("DEBATE_RECENT_WINDOW_MESSAGES") or "14").strip() or "14")),
        ),
        description="How many recent messages (user/judge) to include as conversational context when session_id is used.",
    )
    debate_summary_max_chars: int = Field(
        default_factory=lambda: max(
            200,
            min(20000, int((os.getenv("DEBATE_SUMMARY_MAX_CHARS") or "3500").strip() or "3500")),
        ),
        description="Max characters for the rolling session summary stored on debate_sessions.session_summary.",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()