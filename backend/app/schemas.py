from __future__ import annotations

from pydantic import BaseModel, Field


class Persona(BaseModel):
    id: str = Field(..., description="Unique identifier for the persona.")
    name: str = Field(..., description="Display name for the persona.")
    description: str = Field(..., description="Background traits and context for the persona.")


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


class JudgeConsensus(BaseModel):
    summary: str = Field(..., description="Concise summary of the consensus.")
    reasoning: str = Field(..., description="Judge reasoning that justifies the summary.")
    usage: TokenUsage | None = Field(
        default=None,
        description="Token usage for the judge response (OpenAI).",
    )


class ConsensusResponse(BaseModel):
    personas: list[PersonaAnswer]
    judge: JudgeConsensus
    usage: TokenUsage | None = Field(
        default=None,
        description="Total token usage for the whole request (sum of persona + judge).",
    )

