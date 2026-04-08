from pydantic import BaseModel
from datetime import datetime


class AuthorCreate(BaseModel):
    name: str
    scholar_id: str | None = None
    affiliation: str | None = None
    profile_url: str | None = None


class Author(BaseModel):
    id: int
    name: str
    scholar_id: str | None
    affiliation: str | None
    profile_url: str | None
    raw_json_path: str
    scraped_at: datetime

    class Config:
        from_attributes = True
