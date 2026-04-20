import json
from app.core.llm_client import LLMClient


def execute_annotation_task(persona_json: dict, task_spec: dict) -> dict:
    system_prompt = f"""
You are simulating a Software Engineering researcher persona.

Persona:
{json.dumps(persona_json, indent=2)}

You must perform the task EXACTLY as described,
using this persona's reasoning style and priorities.
"""

    user_prompt = task_spec["prompt"]

    llm = LLMClient()
    response = llm.model.generate_content(
        f"{system_prompt}\n\n{user_prompt}"
    )

    return {
        "task_id": task_spec["task_id"],
        "response": response.text.strip()
    }
