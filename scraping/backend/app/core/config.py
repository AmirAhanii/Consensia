from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://ihaka:123123@localhost:5432/se_personas"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    serpapi_api_key: str = ""
    openai_model: str = "gpt-5.2"
    openai_api_key: str = ""
    openai_temperature: float = 0.0
    data_dir: str = "./data"
    gemini_temperature: float = 0.0 
    cors_allow_origins: str = "http://localhost:5173" 
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("data_dir")
    @classmethod
    def ensure_data_dir(cls, v: str) -> str:
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        (p / "raw_authors").mkdir(parents=True, exist_ok=True)
        (p / "personas").mkdir(parents=True, exist_ok=True)
        return str(p)


settings = Settings()
