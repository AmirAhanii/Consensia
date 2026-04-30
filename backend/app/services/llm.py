from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Iterable

from openai import AsyncAzureOpenAI, AsyncOpenAI

from ..config import Settings
from ..schemas import (
    ConsensusResponse,
    DebateResponse,
    DebateRound,
    JudgeConsensus,
    Persona,
    PersonaAnswer,
    PersonaReasoningQualityQa,
    PersonaTopicRelevanceQa,
    TokenUsage,
)


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

    def _persona_material_block(self, persona: Persona) -> str:
        basis = (persona.persona_basis or "").strip()
        desc = (persona.description or "").strip()
        if basis:
            clipped = basis[:12000] + ("..." if len(basis) > 12000 else "")
            return (
                "REFERENCE_MATERIAL_USED_TO_DEFINE_THIS_PARTICIPANT:\n"
                f"{clipped}\n\n"
                f"SYNTHESIZED_PUBLIC_PROFILE:\n{desc}"
            )
        return f"PERSONA_PROFILE:\n{desc}"

    @staticmethod
    def _normalize_calibration_weights(
        topic: list[PersonaTopicRelevanceQa], reasoning: list[PersonaReasoningQualityQa]
    ) -> dict[str, float]:
        tmap = {x.persona_id: x.score for x in topic}
        rmap = {x.persona_id: x.score for x in reasoning}
        ids = list({*tmap.keys(), *rmap.keys()})
        if not ids:
            return {}
        raw: dict[str, float] = {}
        for pid in ids:
            tv = max(0, min(9, tmap.get(pid, 5)))
            rv = max(0, min(9, rmap.get(pid, 5)))
            raw[pid] = float((tv + 1) * (rv + 1))
        total = sum(raw.values())
        if total <= 0:
            return {pid: 1.0 / len(ids) for pid in ids}
        return {pid: raw[pid] / total for pid in ids}

    def _format_calibration_block(
        self,
        topic: list[PersonaTopicRelevanceQa],
        reasoning: list[PersonaReasoningQualityQa],
        weights: dict[str, float],
        personas: list[Persona],
    ) -> str:
        name_by_id = {p.id: p.name for p in personas}
        lines = [
            "CALIBRATED_SYNTHESIS_WEIGHTS (from two-pass QA: topic fit before answers, argument quality after). "
            "Higher normalized_weight means more influence on the merged consensus.",
            "",
        ]
        for pid in sorted(weights.keys(), key=lambda i: name_by_id.get(i, i)):
            t = next((x for x in topic if x.persona_id == pid), None)
            r = next((x for x in reasoning if x.persona_id == pid), None)
            tr = t.score if t else "?"
            rr = r.score if r else "?"
            tn = (t.rationale[:400] + "…") if t and len(t.rationale) > 400 else (t.rationale if t else "")
            rn = (r.rationale[:400] + "…") if r and len(r.rationale) > 400 else (r.rationale if r else "")
            lines.append(
                f"- {name_by_id.get(pid, pid)} | topic_relevance_0_9={tr} | "
                f"reasoning_quality_0_9={rr} | normalized_weight={weights[pid]:.4f}"
            )
            if tn:
                lines.append(f"    Topic QA: {tn}")
            if rn:
                lines.append(f"    Reasoning QA: {rn}")
        lines.append("")
        lines.append(
            "Apply these weights when merging substantive claims. If the transcript clearly contradicts a score, "
            "follow the transcript and note the discrepancy."
        )
        return "\n".join(lines)

    def _finalize_topic_scores(
        self, personas: list[Persona], rows: list[dict] | None
    ) -> list[PersonaTopicRelevanceQa]:
        by_id = {p.id: p for p in personas}
        out: list[PersonaTopicRelevanceQa] = []
        used: set[str] = set()
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                pid = str(row.get("persona_id") or "").strip()
                if pid not in by_id or pid in used:
                    continue
                used.add(pid)
                raw_s = row.get("topic_relevance", row.get("score", 5))
                try:
                    sc = int(float(raw_s))
                except (TypeError, ValueError):
                    sc = 5
                sc = max(0, min(9, sc))
                rationale = str(row.get("rationale", "")).strip()
                out.append(
                    PersonaTopicRelevanceQa(
                        persona_id=pid, persona_name=by_id[pid].name, score=sc, rationale=rationale
                    )
                )
        for p in personas:
            if p.id not in used:
                out.append(
                    PersonaTopicRelevanceQa(
                        persona_id=p.id,
                        persona_name=p.name,
                        score=5,
                        rationale="[Calibration fallback — model output incomplete]",
                    )
                )
        return sorted(out, key=lambda x: x.persona_id)

    def _finalize_reasoning_scores(
        self, personas: list[Persona], rows: list[dict] | None
    ) -> list[PersonaReasoningQualityQa]:
        by_id = {p.id: p for p in personas}
        out: list[PersonaReasoningQualityQa] = []
        used: set[str] = set()
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                pid = str(row.get("persona_id") or "").strip()
                if pid not in by_id or pid in used:
                    continue
                used.add(pid)
                raw_s = row.get("reasoning_quality", row.get("score", 5))
                try:
                    sc = int(float(raw_s))
                except (TypeError, ValueError):
                    sc = 5
                sc = max(0, min(9, sc))
                rationale = str(row.get("rationale", "")).strip()
                out.append(
                    PersonaReasoningQualityQa(
                        persona_id=pid, persona_name=by_id[pid].name, score=sc, rationale=rationale
                    )
                )
        for p in personas:
            if p.id not in used:
                out.append(
                    PersonaReasoningQualityQa(
                        persona_id=p.id,
                        persona_name=p.name,
                        score=5,
                        rationale="[Calibration fallback — model output incomplete]",
                    )
                )
        return sorted(out, key=lambda x: x.persona_id)

    def _simulate_topic_qa(self, personas: list[Persona]) -> list[PersonaTopicRelevanceQa]:
        return [
            PersonaTopicRelevanceQa(
                persona_id=p.id,
                persona_name=p.name,
                score=6,
                rationale="[Simulated topic relevance — connect a real LLM for calibration.]",
            )
            for p in personas
        ]

    def _simulate_reasoning_qa(self, personas: list[Persona]) -> list[PersonaReasoningQualityQa]:
        return [
            PersonaReasoningQualityQa(
                persona_id=p.id,
                persona_name=p.name,
                score=6,
                rationale="[Simulated reasoning quality — connect a real LLM for calibration.]",
            )
            for p in personas
        ]

    def _debaters_transcript_by_persona(self, personas: list[Persona], rounds: list[DebateRound]) -> dict[str, str]:
        parts: dict[str, list[str]] = {p.id: [] for p in personas}
        for r in rounds:
            for a in r.persona_answers:
                parts.setdefault(a.persona_id, []).append(
                    f"Round {r.round_number} ({r.label}):\n{a.answer}"
                )
        return {pid: "\n\n".join(lines) if lines else "(no utterances)" for pid, lines in parts.items()}

    async def _run_topic_relevance_qa(
        self, question: str, personas: list[Persona]
    ) -> tuple[list[PersonaTopicRelevanceQa], TokenUsage | None]:
        if len(personas) < 2:
            return [], None
        if self._provider is Provider.NONE:
            return self._simulate_topic_qa(personas), None

        blocks = []
        for p in personas:
            blocks.append(
                f"--- PARTICIPANT persona_id={p.id} display_name={p.name} ---\n"
                f"{self._persona_material_block(p)}"
            )
        user = f"QUESTION:\n{question.strip()}\n\n" + "\n\n".join(blocks)
        system = (
            "You are an independent calibration judge. For each participant, using ONLY the question and the "
            "reference material / profile provided for that participant, assign one integer topic_relevance "
            "from 0 to 9 measuring how strongly the question matches their fields and implied knowledge "
            "(0 = unrelated or wrong domain, 5 = partial overlap, 9 = the question sits squarely in their expertise). "
            "Do not invent credentials beyond the supplied text. "
            'Return strict JSON: {"scores":[{"persona_id":"...","persona_name":"...","topic_relevance":<int>,"rationale":"..."}]} '
            "Include every persona_id listed in the user message."
        )

        if self._provider is Provider.OPENAI and self._openai_client:
            assert self._openai_client is not None
            response = await self._openai_client.chat.completions.create(
                model=self._settings.judge_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                max_tokens=min(self._settings.max_output_tokens_judge, 2048),
            )
            content = response.choices[0].message.content or "{}"
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {}
            rows = parsed.get("scores") if isinstance(parsed, dict) else None
            usage = getattr(response, "usage", None)
            tu: TokenUsage | None = None
            if usage:
                tu = TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
            return self._finalize_topic_scores(personas, rows if isinstance(rows, list) else None), tu

        if self._provider is Provider.GEMINI and self._gemini_model is not None:
            prompt = f"{system}\n\n{user}"
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
                    parsed = {}
            rows = parsed.get("scores") if isinstance(parsed, dict) else None
            return self._finalize_topic_scores(personas, rows if isinstance(rows, list) else None), None

        return self._simulate_topic_qa(personas), None

    async def _run_reasoning_quality_qa_consensus(
        self,
        question: str,
        personas: list[Persona],
        answers: list[PersonaAnswer],
    ) -> tuple[list[PersonaReasoningQualityQa], TokenUsage | None]:
        if len(personas) < 2:
            return [], None
        if self._provider is Provider.NONE:
            return self._simulate_reasoning_qa(personas), None

        blocks = []
        for p in personas:
            ans = next((a for a in answers if a.persona_id == p.id), None)
            body = ans.answer if ans else ""
            blocks.append(
                f"--- PARTICIPANT persona_id={p.id} display_name={p.name} ---\n"
                f"{self._persona_material_block(p)}\n\n"
                f"THEIR_SINGLE_RESPONSE:\n{body}"
            )
        user = f"QUESTION:\n{question.strip()}\n\n" + "\n\n".join(blocks)
        system = (
            "You evaluate each participant's response AFTER seeing the question, their reference/profile, and their answer. "
            "Assign reasoning_quality integer 0–9: strength of argument, specificity (penalize lazy or generic answers), "
            "and consistency with the persona implied by the material. "
            "9 = excellent, 0 = vacuous or clearly failing persona standards. "
            'Return strict JSON: {"scores":[{"persona_id":"...","persona_name":"...","reasoning_quality":<int>,"rationale":"..."}]} '
            "Include every persona_id from the user message."
        )

        if self._provider is Provider.OPENAI and self._openai_client:
            assert self._openai_client is not None
            response = await self._openai_client.chat.completions.create(
                model=self._settings.judge_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                max_tokens=min(self._settings.max_output_tokens_judge, 2048),
            )
            content = response.choices[0].message.content or "{}"
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {}
            rows = parsed.get("scores") if isinstance(parsed, dict) else None
            usage = getattr(response, "usage", None)
            tu: TokenUsage | None = None
            if usage:
                tu = TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
            return self._finalize_reasoning_scores(personas, rows if isinstance(rows, list) else None), tu

        if self._provider is Provider.GEMINI and self._gemini_model is not None:
            prompt = f"{system}\n\n{user}"
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
                    parsed = {}
            rows = parsed.get("scores") if isinstance(parsed, dict) else None
            return self._finalize_reasoning_scores(personas, rows if isinstance(rows, list) else None), None

        return self._simulate_reasoning_qa(personas), None

    async def _run_reasoning_quality_qa_debate(
        self,
        question: str,
        personas: list[Persona],
        rounds: list[DebateRound],
    ) -> tuple[list[PersonaReasoningQualityQa], TokenUsage | None]:
        if len(personas) < 2:
            return [], None
        if self._provider is Provider.NONE:
            return self._simulate_reasoning_qa(personas), None

        transcripts = self._debaters_transcript_by_persona(personas, rounds)
        blocks = []
        for p in personas:
            blocks.append(
                f"--- PARTICIPANT persona_id={p.id} display_name={p.name} ---\n"
                f"{self._persona_material_block(p)}\n\n"
                f"ALL_OF_THEIR_UTTERANCES_ACROSS_ROUNDS:\n{transcripts.get(p.id, '')}"
            )
        user = f"QUESTION:\n{question.strip()}\n\n" + "\n\n".join(blocks)
        system = (
            "You evaluate each participant's deliberation AFTER a multi-round debate. "
            "Using the question, their reference/profile, and everything they said across rounds, "
            "assign reasoning_quality integer 0–9: argument strength, engagement with others where visible, "
            "specificity (penalize lazy or generic replies), and consistency with the persona implied by the material. "
            "9 = excellent debate contribution, 0 = vacuous or failing persona standards. "
            'Return strict JSON: {"scores":[{"persona_id":"...","persona_name":"...","reasoning_quality":<int>,"rationale":"..."}]} '
            "Include every persona_id from the user message."
        )

        if self._provider is Provider.OPENAI and self._openai_client:
            assert self._openai_client is not None
            response = await self._openai_client.chat.completions.create(
                model=self._settings.judge_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                max_tokens=min(self._settings.max_output_tokens_judge, 3072),
            )
            content = response.choices[0].message.content or "{}"
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {}
            rows = parsed.get("scores") if isinstance(parsed, dict) else None
            usage = getattr(response, "usage", None)
            tu: TokenUsage | None = None
            if usage:
                tu = TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
            return self._finalize_reasoning_scores(personas, rows if isinstance(rows, list) else None), tu

        if self._provider is Provider.GEMINI and self._gemini_model is not None:
            prompt = f"{system}\n\n{user}"
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
                    parsed = {}
            rows = parsed.get("scores") if isinstance(parsed, dict) else None
            return self._finalize_reasoning_scores(personas, rows if isinstance(rows, list) else None), None

        return self._simulate_reasoning_qa(personas), None

    async def run_consensus_multi(self, question: str, personas: list[Persona]) -> ConsensusResponse:
        """Multi-persona consensus: topic QA → answers → reasoning QA → weighted judge."""
        all_usage: list[TokenUsage] = []
        topic_qa, u_topic = await self._run_topic_relevance_qa(question, personas)
        if u_topic:
            all_usage.append(u_topic)

        persona_answers = list(
            await asyncio.gather(*(self.generate_persona_answer(p, question) for p in personas))
        )
        for a in persona_answers:
            if a.usage:
                all_usage.append(a.usage)

        reasoning_qa, u_rq = await self._run_reasoning_quality_qa_consensus(question, personas, persona_answers)
        if u_rq:
            all_usage.append(u_rq)

        weights = self._normalize_calibration_weights(topic_qa, reasoning_qa)
        cal_block = self._format_calibration_block(topic_qa, reasoning_qa, weights, personas)
        judge = await self.generate_judge_consensus(persona_answers, question, calibration_block=cal_block)
        if judge.usage:
            all_usage.append(judge.usage)

        total_usage: TokenUsage | None = None
        if all_usage:
            total_usage = TokenUsage(
                prompt_tokens=sum(u.prompt_tokens for u in all_usage),
                completion_tokens=sum(u.completion_tokens for u in all_usage),
                total_tokens=sum(u.total_tokens for u in all_usage),
            )

        return ConsensusResponse(
            personas=persona_answers,
            topic_relevance_qa=topic_qa,
            reasoning_quality_qa=reasoning_qa,
            judge=judge,
            usage=total_usage,
        )

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
        calibration_block: str = "",
    ) -> JudgeConsensus:
        if self._provider is Provider.OPENAI and self._openai_client:
            return await self._generate_judge_consensus_openai(
                persona_answers, question, calibration_block
            )

        if self._provider is Provider.GEMINI and self._gemini_model:
            return await self._generate_judge_consensus_gemini(
                persona_answers, question, calibration_block
            )

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
        calibration_block: str = "",
    ) -> JudgeConsensus:
        assert self._openai_client is not None
        persona_sections = self._build_judge_context(persona_answers)
        cal = (calibration_block or "").strip()
        user_body = (
            f"{cal}\n\nQuestion: {question}\n\nPersona responses:\n{persona_sections}"
            if cal
            else f"Question: {question}\n\nPersona responses:\n{persona_sections}"
        )

        response = await self._openai_client.chat.completions.create(
            model=self._settings.judge_model,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an impartial judge. Read the persona responses and any calibration block. "
                        "Deliver:\n"
                        "1. A concise summary of the best consensus.\n"
                        "2. Reasoning that references substantive claims and explains how calibration scores "
                        "influenced weighting when merging viewpoints.\n"
                        "Return JSON with keys 'summary' and 'reasoning'."
                    ),
                },
                {
                    "role": "user",
                    "content": user_body,
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
        calibration_block: str = "",
    ) -> JudgeConsensus:
        assert self._gemini_model is not None
        persona_sections = self._build_judge_context(persona_answers)
        cal = (calibration_block or "").strip()
        user_tail = (
            f"{cal}\n\nQuestion: {question}\n\nPersona responses:\n{persona_sections}"
            if cal
            else f"Question: {question}\n\nPersona responses:\n{persona_sections}"
        )

        prompt = (
            "You are an impartial judge mediating a discussion between expert personas.\n"
            "Read any calibration block, then the persona responses. Return JSON with two fields: "
            "'summary' and 'reasoning'. The summary presents the best collective answer. "
            "The reasoning cites personas and explains how calibration scores influenced the merge.\n"
            f"{user_tail}"
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
        topic_qa: list[PersonaTopicRelevanceQa] = []
        reasoning_qa: list[PersonaReasoningQualityQa] = []

        if len(personas) > 1:
            t_list, u_t = await self._run_topic_relevance_qa(question, personas)
            topic_qa = t_list
            if u_t:
                all_usage.append(u_t)

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
            r_list, u_r = await self._run_reasoning_quality_qa_debate(question, personas, rounds)
            reasoning_qa = r_list
            if u_r:
                all_usage.append(u_r)
            weights = self._normalize_calibration_weights(topic_qa, reasoning_qa)
            cal_block = self._format_calibration_block(topic_qa, reasoning_qa, weights, personas)
            judge = await self._generate_debate_judge(question, rounds, cal_block)
            if judge.usage:
                all_usage.append(judge.usage)

        total_usage: TokenUsage | None = None
        if all_usage:
            total_usage = TokenUsage(
                prompt_tokens=sum(u.prompt_tokens for u in all_usage),
                completion_tokens=sum(u.completion_tokens for u in all_usage),
                total_tokens=sum(u.total_tokens for u in all_usage),
            )

        return DebateResponse(
            rounds=rounds,
            topic_relevance_qa=topic_qa,
            reasoning_quality_qa=reasoning_qa,
            judge=judge,
            usage=total_usage,
        )

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

    async def _generate_debate_judge(
        self,
        question: str,
        rounds: list[DebateRound],
        calibration_block: str,
    ) -> JudgeConsensus:
        if self._provider is Provider.OPENAI and self._openai_client:
            return await self._generate_debate_judge_openai(question, rounds, calibration_block)
        if self._provider is Provider.GEMINI and self._gemini_model:
            return await self._generate_debate_judge_gemini(question, rounds, calibration_block)
        return self._simulate_debate_judge(question, rounds)

    def _build_debate_transcript(self, question: str, rounds: list[DebateRound]) -> str:
        parts = [f"Question: {question.strip()}"]
        for r in rounds:
            parts.append(f"\n--- Round {r.round_number}: {r.label} ---")
            for a in r.persona_answers:
                parts.append(f"{a.persona_name}: {a.answer}")
        return "\n\n".join(parts)

    def _build_debate_judge_user_payload(
        self, question: str, rounds: list[DebateRound], calibration_block: str
    ) -> str:
        cal = (calibration_block or "").strip()
        transcript = self._build_debate_transcript(question, rounds)
        if cal:
            return f"{cal}\n\n{transcript}"
        return transcript

    async def _generate_debate_judge_openai(
        self, question: str, rounds: list[DebateRound], calibration_block: str
    ) -> JudgeConsensus:
        assert self._openai_client is not None
        user_payload = self._build_debate_judge_user_payload(question, rounds, calibration_block)

        response = await self._openai_client.chat.completions.create(
            model=self._settings.judge_model,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an impartial judge observing a structured multi-round debate between expert personas.\n"
                        "You receive a calibration block (topic relevance and reasoning quality scores from independent "
                        "QA passes, plus normalized synthesis weights) and the full transcript.\n"
                        "Deliver:\n"
                        "1. A concise consensus summary capturing key agreements and resolutions.\n"
                        "2. Reasoning explaining which arguments were most compelling, how positions evolved, and "
                        "how you applied the calibration weights when merging viewpoints.\n"
                        "Return JSON with keys 'summary' and 'reasoning'."
                    ),
                },
                {"role": "user", "content": user_payload},
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

    async def _generate_debate_judge_gemini(
        self, question: str, rounds: list[DebateRound], calibration_block: str
    ) -> JudgeConsensus:
        assert self._gemini_model is not None
        user_payload = self._build_debate_judge_user_payload(question, rounds, calibration_block)

        prompt = (
            "You are an impartial judge observing a structured multi-round debate between expert personas.\n"
            "You receive a calibration block (topic fit and reasoning quality scores with normalized weights) "
            "and the full transcript. Return JSON with two fields: 'summary' and 'reasoning'.\n"
            "The summary captures key agreements and resolutions. "
            "The reasoning explains which arguments were most compelling and how calibration influenced the merge.\n\n"
            f"{user_payload}"
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

