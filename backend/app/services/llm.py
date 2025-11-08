from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Iterable

import google.generativeai as genai
from openai import AsyncOpenAI

from ..config import Settings
from ..schemas import JudgeConsensus, Persona, PersonaAnswer


class Provider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    NONE = "none"


class LLMService:
    """
    Wrapper around OpenAI or Gemini (with a simulated fallback) to generate persona answers and judge consensus.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._provider = self._resolve_provider(settings)

        self._openai_client: AsyncOpenAI | None = None
        self._gemini_model = None

        if self._provider is Provider.OPENAI and settings.openai_api_key:
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif self._provider is Provider.GEMINI and settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            model_name = settings.gemini_model
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"
            self._gemini_model = genai.GenerativeModel(model_name=model_name)

    def _resolve_provider(self, settings: Settings) -> Provider:
        choice = settings.llm_provider.lower()
        if choice == "openai":
            return Provider.OPENAI if settings.openai_api_key else Provider.NONE
        if choice == "gemini":
            return Provider.GEMINI if settings.gemini_api_key else Provider.NONE

        # auto mode: prefer OpenAI if available otherwise Gemini, otherwise fallback.
        if settings.openai_api_key:
            return Provider.OPENAI
        if settings.gemini_api_key:
            return Provider.GEMINI
        return Provider.NONE

    async def generate_persona_answer(self, persona: Persona, question: str) -> PersonaAnswer:
        if self._provider is Provider.OPENAI and self._openai_client:
            return await self._generate_persona_answer_openai(persona, question)

        if self._provider is Provider.GEMINI and self._gemini_model:
            return await self._generate_persona_answer_gemini(persona, question)

        simulated = self._simulate_persona_answer(persona, question)
        return PersonaAnswer(
            persona_id=persona.id,
            persona_name=persona.name,
            persona_description=persona.description,
            answer=simulated,
        )

    async def generate_judge_consensus(
        self,
        persona_answers: Iterable[PersonaAnswer],
        question: str,
    ) -> JudgeConsensus:
        if self._provider is Provider.OPENAI and self._openai_client:
            return await self._generate_judge_consensus_openai(persona_answers, question)

        if self._provider is Provider.GEMINI and self._gemini_model:
            return await self._generate_judge_consensus_gemini(persona_answers, question)

        return self._simulate_judge(persona_answers, question)

    async def _generate_persona_answer_openai(self, persona: Persona, question: str) -> PersonaAnswer:
        assert self._openai_client is not None  # for type-checkers

        instructions = self._build_persona_instruction(persona)

        response = await self._openai_client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": instructions,
                },
                {"role": "user", "content": question},
            ],
        )

        content = response.choices[0].message.content or ""
        return PersonaAnswer(
            persona_id=persona.id,
            persona_name=persona.name,
            persona_description=persona.description,
            answer=content.strip(),
        )

    async def _generate_persona_answer_gemini(self, persona: Persona, question: str) -> PersonaAnswer:
        assert self._gemini_model is not None

        prompt = self._build_persona_prompt(persona, question)

        response = await asyncio.to_thread(
            self._gemini_model.generate_content,
            [{"role": "user", "parts": [prompt]}],
        )

        content = (response.text or "").strip()
        return PersonaAnswer(
            persona_id=persona.id,
            persona_name=persona.name,
            persona_description=persona.description,
            answer=content,
        )

    async def _generate_judge_consensus_openai(
        self,
        persona_answers: Iterable[PersonaAnswer],
        question: str,
    ) -> JudgeConsensus:
        assert self._openai_client is not None
        persona_sections = self._build_judge_context(persona_answers)

        response = await self._openai_client.chat.completions.create(
            model=self._settings.judge_model,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an impartial judge. Read the persona responses and deliver:\n"
                        "1. A concise summary that captures the best consensus.\n"
                        "2. A reasoning section that references the personas' points.\n"
                        "Return JSON with keys 'summary' and 'reasoning'."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Persona responses:\n{persona_sections}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        message = response.choices[0].message
        if message.parsed and isinstance(message.parsed, dict):
            parsed = message.parsed
        else:
            parsed = {"summary": message.content or "", "reasoning": ""}

        return JudgeConsensus(
            summary=parsed.get("summary", "").strip(),
            reasoning=parsed.get("reasoning", "").strip(),
        )

    async def _generate_judge_consensus_gemini(
        self,
        persona_answers: Iterable[PersonaAnswer],
        question: str,
    ) -> JudgeConsensus:
        assert self._gemini_model is not None
        persona_sections = self._build_judge_context(persona_answers)

        prompt = (
            "You are an impartial judge mediating a discussion between expert personas.\n"
            "Read the persona responses and return JSON with two fields: 'summary' and 'reasoning'.\n"
            "The summary should present the best collective answer. The reasoning should cite the personas' points.\n"
            f"Question: {question}\n\nPersona responses:\n{persona_sections}"
        )

        response = await asyncio.to_thread(
            self._gemini_model.generate_content,
            [{"role": "user", "parts": [prompt]}],
        )

        text = (response.text or "").strip()
        parsed: dict[str, str]
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Gemini may return code fences; attempt to clean.
            cleaned = text.strip("` \n")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                parsed = {
                    "summary": text,
                    "reasoning": "Judge response could not be parsed as JSON.",
                }

        return JudgeConsensus(
            summary=parsed.get("summary", "").strip(),
            reasoning=parsed.get("reasoning", "").strip(),
        )

    def _simulate_persona_answer(self, persona: Persona, question: str) -> str:
        return (
            f"[Simulated response for {persona.name}]\n"
            f'As {persona.description}, here is a high-level take on "{question.strip()}".'
        )

    def _build_persona_instruction(self, persona: Persona) -> str:
        return (
            "You are an AI agent participating in a structured debate.\n"
            f"Your persona name: {persona.name}\n"
            f"Persona background: {persona.description}\n"
            "Role-play this character faithfully, adopt their tone, priorities, and level of expertise.\n"
            "Keep the response concise (3-6 sentences) unless deeper analysis is required."
        )

    def _build_persona_prompt(self, persona: Persona, question: str) -> str:
        instructions = self._build_persona_instruction(persona)
        return (
            f"{instructions}\n"
            "Question:\n"
            f"{question.strip()}"
        )

    def _build_judge_context(self, persona_answers: Iterable[PersonaAnswer]) -> str:
        sections = []
        for answer in persona_answers:
            # judge needs access to persona metadata; reuse persona description from payload
            sections.append(
                f"Persona ID: {answer.persona_id}\n"
                f"Persona Name: {answer.persona_name}\n"
                f"Persona Background: {answer.persona_description}\n"
                f"Response:\n{answer.answer}"
            )
        return "\n\n".join(sections)

    def _simulate_judge(self, persona_answers: Iterable[PersonaAnswer], question: str) -> JudgeConsensus:
        concatenated = " ".join(answer.answer for answer in persona_answers)
        summary = (
            "[Simulated consensus]\n"
            f'The personas considered the question "{question.strip()}" and identified key ideas.'
        )
        reasoning = (
            "[Simulated reasoning]\n"
            "This placeholder consensus aggregates the persona responses for development testing.\n"
            f"Combined persona insights: {concatenated[:240]}..."
        )
        return JudgeConsensus(summary=summary, reasoning=reasoning)

