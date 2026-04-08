from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.db.database import Base


class Persona(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False, default="v1")
    model_name = Column(String, nullable=False, default="gemini-2.0-flash")
    persona_json_path = Column(String, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
