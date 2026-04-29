from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


CHUNK_SIZE = 5


# ── Pydantic schemas for structured OpenAI outputs ────────────────────────────

class Stage1Summary(BaseModel):
    chunk_id: int
    primary_themes: list[str]
    secondary_themes: list[str]
    methodologies: list[str]
    recurring_concepts: list[str]
    knowledge_signals: list[str] = Field(
        description="Topics and domains the author studies — objective research content."
    )
    style_signals: list[str] = Field(
        description="How the author reasons — empirical vs theoretical, evidence types, argumentation style."
    )
    summary: str


class Stage2Profile(BaseModel):
    primary_research_themes: list[str]
    secondary_research_themes: list[str]
    methodological_traits: list[str]
    recurring_concepts: list[str]
    communication_indicators: list[str]
    researcher_summary: str


class ReflectionInsight(BaseModel):
    insight: str
    evidence: list[str]


class Stage25Reflection(BaseModel):
    reasoning: str
    behavioral_insights: list[ReflectionInsight]
    evaluation_approach: str


class DomainWeights(BaseModel):
    maintainability: float
    readability: float
    performance: float
    correctness: float
    security: float
    architecture: float
    developer_experience: float
    testing_quality: float
    static_analysis_rigor: float
    refactoring_quality: float


class MethodologicalProfile(BaseModel):
    typical_methods: list[str]
    evidence_preferences: str
    research_philosophy: str


class CommunicationStyle(BaseModel):
    tone: str
    voice: str
    preferred_structure: list[str]


class AnnotationFocus(BaseModel):
    primary_concerns: list[str]
    secondary_concerns: list[str]
    quality_indicators: list[str]


class EvaluationStyle(BaseModel):
    decision_making_traits: list[str]
    biases: list[str]
    limitations: list[str]


class Stage3Features(BaseModel):
    reasoning_process: str
    domain_focus_weights: DomainWeights
    methodological_profile: MethodologicalProfile
    communication_style: CommunicationStyle
    evaluation_style: EvaluationStyle
    annotation_focus: AnnotationFocus
    conceptual_references: list[str]
    persona_voice: str


# ── Prompts ───────────────────────────────────────────────────────────────────

_S1_SYSTEM = """
You are an expert in Software Engineering research analysis.
Analyze this batch of publications from a single author.

Distinguish between:
- knowledge_signals: TOPICS and DOMAINS the author studies
- style_signals: HOW the author reasons — empirical vs theoretical, evidence types, argumentation

CRITICAL RULES: Do NOT invent missing information. Ground everything in provided paper data.
"""

_S2_SYSTEM = """
You are an expert in distilling Software Engineering research patterns into factual researcher profiles.
Combine the provided chunk summaries into a single, holistic research identity.
CRITICAL RULES: Do NOT add new research areas not in the chunks. Mark weak patterns as uncertain.
"""

_S25_SYSTEM = """
You are an expert in behavioral inference for Software Engineering researchers.
Given a researcher's publication profile, generate HIGH-LEVEL BEHAVIORAL INSIGHTS
explaining how their background would shape their JUDGMENT when evaluating code quality tasks.

Do NOT describe what they study. INFER how their background makes them EVALUATE and PRIORITIZE.
Every behavioral insight must be grounded in specific research evidence.
"""

_S3_SYSTEM = """
You are an expert in modeling Software Engineering researcher behavior.
Transform the provided global research profile AND behavioral reflection insights into structured persona features.
CRITICAL RULES: Your reasoning_process MUST explicitly reference the behavioral_insights and evaluation_approach.
"""


# ── LLM client ────────────────────────────────────────────────────────────────

class _PipelineLLM:
    def __init__(self, client: Any, openai_model: str) -> None:
        self._client = client
        self._model = openai_model

    def generate_structured(self, system: str, prompt: str, schema: type) -> dict:
        response = self._client.beta.chat.completions.parse(
            model=self._model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system.strip()},
                {"role": "user", "content": prompt.strip()},
            ],
            response_format=schema,
        )
        parsed = response.choices[0].message.parsed
        return parsed.model_dump() if parsed is not None else {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_author_context(raw_author: dict) -> dict:
    raw_data = raw_author.get("raw_data", {})
    profile = raw_data.get("serpapi_profile_response", {}).get("author", {})
    interests = profile.get("interests", [])
    co_authors = raw_data.get("serpapi_profile_response", {}).get("co_authors", [])
    table = profile.get("cited_by", {}).get("table", [])
    h_entry = next((t for t in table if "h_index" in t), {})
    return {
        "declared_interests": [i.get("title", "") for i in interests if i.get("title")],
        "co_authors": [ca.get("name", "") for ca in co_authors if ca.get("name")],
        "total_citations": table[0].get("citations", {}).get("all", 0) if table else 0,
        "h_index": h_entry.get("h_index", {}).get("all", 0),
    }


def _chunk_papers(papers: list, size: int = CHUNK_SIZE) -> list:
    return [papers[i:i + size] for i in range(0, len(papers), size)]


def _build_inference_summary(
    author_name: str,
    raw_author: dict,
    profile: dict,
    features: dict,
    reflection: dict,
) -> str:
    primary = ", ".join(profile.get("primary_research_themes", [])[:3])
    eval_approach = reflection.get("evaluation_approach", "")
    tone = features.get("communication_style", {}).get("tone", "")
    voice = features.get("persona_voice", "")
    limitations = "; ".join(features.get("evaluation_style", {}).get("limitations", [])[:2])
    affiliation = raw_author.get("affiliation", "")
    return (
        f"{author_name} is a Software Engineering researcher"
        f"{' at ' + affiliation if affiliation else ''}, "
        f"focused on {primary}. "
        f"Evaluation approach: {eval_approach} "
        f"Communication style: {tone}. "
        f"Known limitations: {limitations}. "
        f"Voice: {voice}"
    ).strip()


# ── Pipeline entry point ──────────────────────────────────────────────────────

def generate_persona_from_raw(
    raw_author: dict[str, Any],
    author_name: str,
    client: Any,
    openai_model: str,
) -> dict[str, Any]:
    llm = _PipelineLLM(client, openai_model)
    papers = raw_author.get("papers", [])
    author_context = _extract_author_context(raw_author)
    paper_chunks = _chunk_papers(papers, CHUNK_SIZE)

    # Stage 1: chunked extraction
    chunks = []
    for i, chunk in enumerate(paper_chunks):
        s1_prompt = (
            f"Author declared research interests: {author_context['declared_interests']}\n\n"
            f"Analyze these papers (chunk {i + 1} of {len(paper_chunks)}):\n"
            f"{json.dumps(chunk, ensure_ascii=False)}"
        )
        summary = llm.generate_structured(_S1_SYSTEM, s1_prompt, Stage1Summary)
        summary["chunk_id"] = i
        chunks.append(summary)

    # Stage 2: global profile synthesis
    s2_prompt = (
        f"Author context:\n{json.dumps(author_context, ensure_ascii=False)}\n\n"
        f"Synthesize these {len(chunks)} chunk summaries:\n"
        f"{json.dumps(chunks, ensure_ascii=False)}"
    )
    profile = llm.generate_structured(_S2_SYSTEM, s2_prompt, Stage2Profile)

    # Stage 2.5: behavioral reflection
    s25_prompt = (
        f"Researcher: {author_name}\n"
        f"Affiliation: {raw_author.get('affiliation', 'Unknown')}\n"
        f"Declared interests: {author_context['declared_interests']}\n"
        f"h-index: {author_context.get('h_index', 'Unknown')}\n\n"
        f"Research profile:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
        "Generate high-level behavioral insights about how this researcher would approach "
        "code quality evaluation. Do not describe their research — infer their evaluation behavior."
    )
    reflection = llm.generate_structured(_S25_SYSTEM, s25_prompt, Stage25Reflection)

    # Stage 3: structured features with CoT
    s3_prompt = (
        f"Research profile:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
        f"Behavioral reflection:\n{json.dumps(reflection, ensure_ascii=False)}\n\n"
        "Generate structured persona features. Your reasoning_process must explicitly "
        "reference the behavioral_insights and evaluation_approach from the reflection."
    )
    features = llm.generate_structured(_S3_SYSTEM, s3_prompt, Stage3Features)

    # Stage 4: deterministic assembly
    annotation_rules: list[str] = []
    for concern in features.get("annotation_focus", {}).get("primary_concerns", []):
        annotation_rules.append(f"Prioritize issues related to: {concern}")
    eval_approach = reflection.get("evaluation_approach", "")
    if eval_approach:
        annotation_rules.append(f"Overall evaluation approach: {eval_approach}")

    inference_summary = _build_inference_summary(
        author_name, raw_author, profile, features, reflection
    )

    return {
        "name": author_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "core_identity": {
            "summary": profile.get("researcher_summary", ""),
            "academic_orientation": raw_author.get("affiliation", ""),
            "primary_research_themes": profile.get("primary_research_themes", []),
        },
        "methodological_profile": features.get("methodological_profile", {}),
        "domain_focus_weights": features.get("domain_focus_weights", {}),
        "communication_style": features.get("communication_style", {}),
        "evaluation_style": features.get("evaluation_style", {}),
        "annotation_focus": features.get("annotation_focus", {}),
        "annotation_rules": annotation_rules,
        "conceptual_references": features.get("conceptual_references", []),
        "persona_voice": features.get("persona_voice", ""),
        "inference_summary": inference_summary,
    }
