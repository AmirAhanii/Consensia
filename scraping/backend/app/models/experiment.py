from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from datetime import datetime
from app.db.database import Base


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id"))
    task_id = Column(String)
    input_payload = Column(JSON)
    output_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
