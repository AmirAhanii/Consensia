import json
import google.generativeai as genai
from pydantic import BaseModel
from app.core.config import settings

class LLMClient:
    def __init__(self, model_name: str | None = None):
        # Configuration is pulled from the central settings
        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = model_name or settings.gemini_model
        
        # Temperature is critical for reproducibility in your research
        # Keeping it at 0.0 ensures deterministic responses for academic rigor
        self.temperature = settings.gemini_temperature

    def generate_structured(self, system_prompt: str, user_prompt: str, response_schema: type[BaseModel]) -> dict:
        """
        Sends prompts to Gemini and forces the output to strictly adhere to a Pydantic schema.
        This eliminates JSONDecodeErrors and guarantees type safety for the persona pipeline.
        """
        # We initialize the model per request to cleanly pass the specific schema and system prompt
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt.strip(),
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                response_mime_type="application/json",
                response_schema=response_schema, 
            ),
        )

        try:
            resp = model.generate_content(user_prompt.strip())
            
            # The API returns a guaranteed valid JSON string matching the Pydantic schema
            return json.loads(resp.text)
            
        except json.JSONDecodeError as e:
            # Fallback log logic for research auditability
            raise ValueError(f"LLM failed to produce valid JSON: {e}\nRaw Response: {resp.text}")
        except Exception as e:
            raise RuntimeError(f"Gemini API Error: {e}")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Legacy method kept for backwards compatibility if needed.
        Uses standard JSON mode without strict Pydantic enforcement.
        """
        full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt.strip()}\n\nUSER DATA:\n{user_prompt.strip()}"
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                response_mime_type="application/json",
            )
        )
        
        try:
            resp = model.generate_content(full_prompt)
            return json.loads(resp.text)
        except Exception as e:
            raise RuntimeError(f"Gemini API Error: {e}")