from pydantic import BaseModel
from datetime import datetime


class Persona(BaseModel):
    id: int
    author_id: int | None
    name: str
    version: str
    model_name: str
    persona_json_path: str
    generated_at: datetime

    class Config:
        from_attributes = True


class AskPersonaRequest(BaseModel):
    question: str
