from pydantic import BaseModel
from datetime import datetime
from typing import Any, Dict


class ExperimentRun(BaseModel):
    id: int
    persona_id: int
    task_id: str
    input_payload: Dict[str, Any]
    output_payload: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ExperimentTask(BaseModel):
    task_id: str
    prompt: str
    metadata: Dict[str, Any] | None = None


class ExperimentExecutionRequest(BaseModel):
    persona_id: int
    task: ExperimentTask
