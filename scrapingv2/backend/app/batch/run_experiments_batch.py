from app.db.database import SessionLocal, engine, Base
from app.models.author import Author
from app.models.persona import Persona
from app.models.experiment import ExperimentRun
from app.services.file_store import load_persona_json_by_path
from app.services.experiment_executor import execute_annotation_task

Base.metadata.create_all(bind=engine)
TASK = {
    "task_id": "code_annotation_1",
    "prompt": """
You are given two code snippets.
Annotate the differences and justify your reasoning.
"""
}

db = SessionLocal()

personas = db.query(Persona).all()

for persona in personas:
    persona_json = load_persona_json_by_path(persona.persona_json_path)
    result = execute_annotation_task(persona_json, TASK)

    db.add(ExperimentRun(
        persona_id=persona.id,
        task_id=TASK["task_id"],
        input_payload=TASK,
        output_payload=result
    ))
    db.commit()

print("Experiments complete.")
