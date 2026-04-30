from __future__ import annotations

from pydantic import BaseModel, Field


class Persona(BaseModel):
    id: str = Field(..., description="Unique identifier for the persona.")
    name: str = Field(..., description="Display name for the persona.")
    description: str = Field(..., description="Background traits and context for the persona.")
    persona_basis: str | None = Field(
        default=None,
        max_length=32000,
        description=(
            "Optional source material used to construct this persona (CV text, researcher profile, etc.). "
            "When set, judge calibration uses it together with the description."
        ),
    )


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(..., ge=0, description="Number of prompt tokens.")
    completion_tokens: int = Field(..., ge=0, description="Number of completion tokens.")
    total_tokens: int = Field(..., ge=0, description="Total tokens (prompt + completion).")


class ConsensusRequest(BaseModel):
    question: str = Field(..., description="The user question to route through personas.")
    personas: list[Persona] = Field(..., description="Ordered list of personas to respond.")


class PersonaAnswer(BaseModel):
    persona_id: str = Field(..., description="Identifier of the persona that generated the answer.")
    persona_name: str = Field(..., description="Display name of the persona.")
    persona_description: str = Field(..., description="Background traits of the persona.")
    answer: str = Field(..., description="The generated answer content.")
    usage: TokenUsage | None = Field(
        default=None,
        description="Token usage for this persona response (OpenAI).",
    )


class PersonaTopicRelevanceQa(BaseModel):
    """Pre-debate: how well the question matches each persona's domain (0–9)."""

    persona_id: str
    persona_name: str
    score: int = Field(..., ge=0, le=9, description="Topic relevance 0 unrelated … 9 highly aligned.")
    rationale: str = ""


class PersonaReasoningQualityQa(BaseModel):
    """Post-debate: argument quality vs persona standards (0–9)."""

    persona_id: str
    persona_name: str
    score: int = Field(..., ge=0, le=9, description="Reasoning quality after their answers.")
    rationale: str = ""


class JudgeConsensus(BaseModel):
    summary: str = Field(..., description="Concise summary of the consensus.")
    reasoning: str = Field(..., description="Judge reasoning that justifies the summary.")
    usage: TokenUsage | None = Field(
        default=None,
        description="Token usage for the judge response (OpenAI).",
    )


class ConsensusResponse(BaseModel):
    personas: list[PersonaAnswer]
    topic_relevance_qa: list[PersonaTopicRelevanceQa] = Field(
        default_factory=list,
        description="Per-persona topic fit scores (empty for single-persona runs).",
    )
    reasoning_quality_qa: list[PersonaReasoningQualityQa] = Field(
        default_factory=list,
        description="Per-persona argument quality after answers (empty for single-persona runs).",
    )
    judge: JudgeConsensus
    usage: TokenUsage | None = Field(
        default=None,
        description="Total token usage for the whole request (sum of persona + judge).",
    )


class DebateRound(BaseModel):
    round_number: int = Field(..., ge=1, description="1-indexed round number.")
    label: str = Field(..., description="Human-readable label for this round.")
    persona_answers: list[PersonaAnswer]


class DebateRequest(BaseModel):
    question: str = Field(..., description="The debate question.")
    personas: list[Persona] = Field(..., description="Personas to debate.")
    num_rounds: int = Field(default=2, ge=1, le=3, description="Number of debate rounds.")


class DebateResponse(BaseModel):
    rounds: list[DebateRound]
    topic_relevance_qa: list[PersonaTopicRelevanceQa] = Field(default_factory=list)
    reasoning_quality_qa: list[PersonaReasoningQualityQa] = Field(default_factory=list)
    judge: JudgeConsensus
    usage: TokenUsage | None = None
