from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Iterable

from openai import AsyncAzureOpenAI, AsyncOpenAI

from ..config import Settings
from ..schemas import DebateResponse, DebateRound, JudgeConsensus, Persona, PersonaAnswer, TokenUsage


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
            # If OPENAI_API_VERSION is set, treat OPENAI_BASE_URL as an Azure endpoint.
            if settings.openai_api_version:
                if not settings.openai_base_url:
                    raise ValueError(
                        "OPENAI_BASE_URL is required for Azure OpenAI (use the Azure endpoint URL)."
                    )
                self._openai_client = AsyncAzureOpenAI(
                    api_key=settings.openai_api_key,
                    azure_endpoint=settings.openai_base_url,
                    api_version=settings.openai_api_version,
                )
            else:
                # OpenAI-compatible endpoints (optional base_url).
                if settings.openai_base_url:
                    self._openai_client = AsyncOpenAI(
                        api_key=settings.openai_api_key,
                        base_url=settings.openai_base_url,
                    )
                else:
                    self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif self._provider is Provider.GEMINI and settings.gemini_api_key:
            # Lazy import so OpenAI-only deployments don't emit Gemini import warnings.
            import google.generativeai as genai

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
            max_tokens=self._settings.max_output_tokens_persona,
        )

        usage = getattr(response, "usage", None)
        token_usage: TokenUsage | None = None
        if usage:
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )

        content = response.choices[0].message.content or ""
        return PersonaAnswer(
            persona_id=persona.id,
            persona_name=persona.name,
            persona_description=persona.description,
            answer=content.strip(),
            usage=token_usage,
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
                        "1. A concise summary of the best consensus.\n"
                        "2. A short reasoning section referencing which personas support the summary.\n"
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
            max_tokens=self._settings.max_output_tokens_judge,
        )

        message = response.choices[0].message
        parsed_message = getattr(message, "parsed", None)
        if parsed_message and isinstance(parsed_message, dict):
            parsed = parsed_message
        else:
            content = message.content or ""
            try:
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    parsed = {"summary": content, "reasoning": ""}
            except json.JSONDecodeError:
                parsed = {"summary": content, "reasoning": ""}

        usage = getattr(response, "usage", None)
        token_usage: TokenUsage | None = None
        if usage:
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )

        return JudgeConsensus(
            summary=parsed.get("summary", "").strip(),
            reasoning=parsed.get("reasoning", "").strip(),
            usage=token_usage,
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

    async def run_debate(
        self, question: str, personas: list[Persona], num_rounds: int = 2
    ) -> DebateResponse:
        rounds: list[DebateRound] = []
        all_usage: list[TokenUsage] = []

        round1_answers = list(await asyncio.gather(
            *(self.generate_persona_answer(persona, question) for persona in personas)
        ))
        for a in round1_answers:
            if a.usage:
                all_usage.append(a.usage)
        rounds.append(DebateRound(round_number=1, label="Initial Positions", persona_answers=round1_answers))

        if len(personas) > 1:
            for round_num in range(2, num_rounds + 1):
                prev = rounds[-1].persona_answers
                label = "Final Remarks" if round_num > 2 else "Rebuttals"
                rebuttal_answers = list(await asyncio.gather(
                    *(self._generate_rebuttal(
                        persona, question,
                        [a for a in prev if a.persona_id != persona.id],
                    ) for persona in personas)
                ))
                for a in rebuttal_answers:
                    if a.usage:
                        all_usage.append(a.usage)
                rounds.append(DebateRound(round_number=round_num, label=label, persona_answers=rebuttal_answers))

        if len(personas) == 1:
            only = rounds[0].persona_answers[0]
            judge = JudgeConsensus(
                summary=only.answer,
                reasoning="Single-persona mode: consensus derived directly from the persona response.",
            )
        else:
            judge = await self._generate_debate_judge(question, rounds)
            if judge.usage:
                all_usage.append(judge.usage)

        total_usage: TokenUsage | None = None
        if all_usage:
            total_usage = TokenUsage(
                prompt_tokens=sum(u.prompt_tokens for u in all_usage),
                completion_tokens=sum(u.completion_tokens for u in all_usage),
                total_tokens=sum(u.total_tokens for u in all_usage),
            )

        return DebateResponse(rounds=rounds, judge=judge, usage=total_usage)

    async def _generate_rebuttal(
        self, persona: Persona, question: str, other_answers: list[PersonaAnswer]
    ) -> PersonaAnswer:
        if self._provider is Provider.OPENAI and self._openai_client:
            return await self._generate_rebuttal_openai(persona, question, other_answers)
        if self._provider is Provider.GEMINI and self._gemini_model:
            return await self._generate_rebuttal_gemini(persona, question, other_answers)
        return self._simulate_rebuttal(persona, question, other_answers)

    async def _generate_rebuttal_openai(
        self, persona: Persona, question: str, other_answers: list[PersonaAnswer]
    ) -> PersonaAnswer:
        assert self._openai_client is not None
        others_text = "\n\n".join(f"{a.persona_name}: {a.answer}" for a in other_answers)
        user_message = (
            f"The debate question is: {question.strip()}\n\n"
            f"Other participants have responded:\n{others_text}\n\n"
            "Now respond as your persona. Engage directly with the other viewpoints — "
            "agree where you find merit, push back where you disagree, refine your stance. "
            "Stay strictly within the expertise described in your background. "
            "If a point raised is outside your domain, acknowledge that and respond only from what you know. "
            "Keep it concise (2-3 sentences)."
        )

        response = await self._openai_client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": self._build_persona_instruction(persona)},
                {"role": "user", "content": user_message},
            ],
            max_tokens=self._settings.max_output_tokens_persona,
        )

        usage = getattr(response, "usage", None)
        token_usage: TokenUsage | None = None
        if usage:
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )

        content = response.choices[0].message.content or ""
        return PersonaAnswer(
            persona_id=persona.id,
            persona_name=persona.name,
            persona_description=persona.description,
            answer=content.strip(),
            usage=token_usage,
        )

    async def _generate_rebuttal_gemini(
        self, persona: Persona, question: str, other_answers: list[PersonaAnswer]
    ) -> PersonaAnswer:
        assert self._gemini_model is not None
        others_text = "\n\n".join(f"{a.persona_name}: {a.answer}" for a in other_answers)
        prompt = (
            f"{self._build_persona_instruction(persona)}\n\n"
            f"The debate question is: {question.strip()}\n\n"
            f"Other participants have responded:\n{others_text}\n\n"
            "Now respond as your persona. Engage directly with the other viewpoints — "
            "agree where you find merit, push back where you disagree, refine your stance. "
            "Stay strictly within the expertise described in your background. "
            "If a point raised is outside your domain, acknowledge that and respond only from what you know. "
            "Keep it concise (2-3 sentences)."
        )

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

    def _simulate_rebuttal(
        self, persona: Persona, question: str, other_answers: list[PersonaAnswer]
    ) -> PersonaAnswer:
        other_names = ", ".join(a.persona_name for a in other_answers)
        return PersonaAnswer(
            persona_id=persona.id,
            persona_name=persona.name,
            persona_description=persona.description,
            answer=(
                f"[Simulated rebuttal for {persona.name}]\n"
                f"Having read the responses from {other_names}, I agree on some points "
                f"but would push back on the framing around '{question.strip()[:60]}'."
            ),
        )

    async def _generate_debate_judge(self, question: str, rounds: list[DebateRound]) -> JudgeConsensus:
        if self._provider is Provider.OPENAI and self._openai_client:
            return await self._generate_debate_judge_openai(question, rounds)
        if self._provider is Provider.GEMINI and self._gemini_model:
            return await self._generate_debate_judge_gemini(question, rounds)
        return self._simulate_debate_judge(question, rounds)

    def _build_debate_transcript(self, question: str, rounds: list[DebateRound]) -> str:
        parts = [f"Question: {question.strip()}"]
        for r in rounds:
            parts.append(f"\n--- Round {r.round_number}: {r.label} ---")
            for a in r.persona_answers:
                parts.append(f"{a.persona_name}: {a.answer}")
        return "\n\n".join(parts)

    async def _generate_debate_judge_openai(self, question: str, rounds: list[DebateRound]) -> JudgeConsensus:
        assert self._openai_client is not None
        transcript = self._build_debate_transcript(question, rounds)

        response = await self._openai_client.chat.completions.create(
            model=self._settings.judge_model,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an impartial judge observing a structured multi-round debate between expert personas.\n"
                        "Read the full transcript and deliver:\n"
                        "1. A concise consensus summary capturing key agreements and resolutions.\n"
                        "2. Reasoning explaining which arguments were most compelling and how positions evolved.\n"
                        "Return JSON with keys 'summary' and 'reasoning'."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            response_format={"type": "json_object"},
            max_tokens=self._settings.max_output_tokens_judge,
        )

        message = response.choices[0].message
        parsed_message = getattr(message, "parsed", None)
        if parsed_message and isinstance(parsed_message, dict):
            parsed = parsed_message
        else:
            content = message.content or ""
            try:
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    parsed = {"summary": content, "reasoning": ""}
            except json.JSONDecodeError:
                parsed = {"summary": content, "reasoning": ""}

        usage = getattr(response, "usage", None)
        token_usage: TokenUsage | None = None
        if usage:
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )

        return JudgeConsensus(
            summary=parsed.get("summary", "").strip(),
            reasoning=parsed.get("reasoning", "").strip(),
            usage=token_usage,
        )

    async def _generate_debate_judge_gemini(self, question: str, rounds: list[DebateRound]) -> JudgeConsensus:
        assert self._gemini_model is not None
        transcript = self._build_debate_transcript(question, rounds)

        prompt = (
            "You are an impartial judge observing a structured multi-round debate between expert personas.\n"
            "Read the full transcript and return JSON with two fields: 'summary' and 'reasoning'.\n"
            "The summary captures key agreements and resolutions. "
            "The reasoning explains which arguments were most compelling.\n\n"
            f"{transcript}"
        )

        response = await asyncio.to_thread(
            self._gemini_model.generate_content,
            [{"role": "user", "parts": [prompt]}],
        )

        text = (response.text or "").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            cleaned = text.strip("` \n")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                parsed = {"summary": text, "reasoning": "Judge response could not be parsed as JSON."}

        return JudgeConsensus(
            summary=parsed.get("summary", "").strip(),
            reasoning=parsed.get("reasoning", "").strip(),
        )

    def _simulate_debate_judge(self, question: str, rounds: list[DebateRound]) -> JudgeConsensus:
        all_names: set[str] = set()
        for r in rounds:
            for a in r.persona_answers:
                all_names.add(a.persona_name)
        names_str = ", ".join(sorted(all_names))
        return JudgeConsensus(
            summary=(
                f"[Simulated debate consensus]\n"
                f'After {len(rounds)} rounds on "{question.strip()[:80]}", '
                "the personas reached a nuanced shared understanding."
            ),
            reasoning=(
                f"[Simulated reasoning]\n"
                f"Participants ({names_str}) engaged across {len(rounds)} rounds. "
                "In a real run, the judge would synthesize agreements and disagreements from the transcript."
            ),
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
            "Role-play this character faithfully, adopting their tone, priorities, and level of expertise.\n"
            "KNOWLEDGE BOUNDARIES: Only speak from the expertise described in your background. "
            "If the question falls outside your domain, explicitly say so (e.g. 'This is outside my area of expertise') "
            "and contribute only what your background genuinely allows. Never fabricate knowledge you would not have.\n"
            "Keep the response very concise (2-3 sentences). Prefer short, high-signal reasoning."
        )

    def _build_persona_prompt(self, persona: Persona, question: str) -> str:
        instructions = self._build_persona_instruction(persona)
        return (
            f"{instructions}\n"
            "Question:\n"
            f"{question.strip()}"
        )

    def _build_judge_context(self, persona_answers: Iterable[PersonaAnswer]) -> str:
        max_chars = self._settings.judge_context_max_chars_per_persona
        sections = []
        for answer in persona_answers:
            # judge needs access to persona metadata; reuse persona description from payload
            resp = answer.answer or ""
            if len(resp) > max_chars:
                resp = resp[:max_chars].rstrip() + "...[truncated]"
            sections.append(
                f"Persona ID: {answer.persona_id}\n"
                f"Persona Name: {answer.persona_name}\n"
                f"Persona Background: {answer.persona_description}\n"
                f"Response:\n{resp}"
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

