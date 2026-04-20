from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.llm_client import LLMClient

# ==========================================
# CONFIGURATION
# ==========================================
CHUNK_SIZE = 5  # Max papers per Stage 1 chunk — prevents Lost in the Middle degradation


# ==========================================
# PYDANTIC SCHEMAS (STRUCTURED OUTPUTS)
# Technique: Constrained Decoding / Schema Enforcement
# ==========================================

class Stage1Summary(BaseModel):
    chunk_id: int
    primary_themes: List[str]
    secondary_themes: List[str]
    methodologies: List[str]
    recurring_concepts: List[str]
    # Objective/Subjective split — PersLLM Paper, Section 3.1 Material Classification
    knowledge_signals: List[str] = Field(
        description="Topics and domains the author studies — objective research content."
    )
    style_signals: List[str] = Field(
        description="How the author reasons and argues — empirical vs theoretical preference, "
                    "confidence level, hedging patterns, argumentation style."
    )
    summary: str


class Stage2Profile(BaseModel):
    primary_research_themes: List[str]
    secondary_research_themes: List[str]
    methodological_traits: List[str]
    recurring_concepts: List[str]
    communication_indicators: List[str]
    researcher_summary: str


class ReflectionInsight(BaseModel):
    insight: str = Field(description="A high-level behavioral inference about evaluation style.")
    evidence: List[str] = Field(description="Specific research patterns that support this insight.")

# Stage 2.5 Reflection — Generative Agents Paper, Section 4.2
# out_of_scope_domains removed: scraped papers do not fully represent
# the person's knowledge scope, so domain exclusion cannot be reliably inferred.
class Stage25Reflection(BaseModel):
    reasoning: str = Field(
        description="Step-by-step reasoning connecting publication history to evaluation behavior."
    )
    behavioral_insights: List[ReflectionInsight] = Field(
        description="High-level insights about how this researcher would approach code quality judgments."
    )
    evaluation_approach: str = Field(
        description="A concise description of this researcher's likely approach to evaluating code tasks."
    )


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
    typical_methods: List[str]
    evidence_preferences: str
    research_philosophy: str


class CommunicationStyle(BaseModel):
    tone: str
    voice: str
    preferred_structure: List[str]


class AnnotationFocus(BaseModel):
    primary_concerns: List[str]
    secondary_concerns: List[str]
    quality_indicators: List[str]


class EvaluationStyle(BaseModel):
    decision_making_traits: List[str]
    biases: List[str]
    limitations: List[str]


class Stage3Features(BaseModel):
    # CoT Forcing — reasoning_process must reference reflection insights
    reasoning_process: str = Field(
        description="Step-by-step logic justifying these features. "
                    "Must explicitly reference the behavioral reflection insights, not just raw research topics."
    )
    domain_focus_weights: DomainWeights
    methodological_profile: MethodologicalProfile
    communication_style: CommunicationStyle
    evaluation_style: EvaluationStyle
    annotation_focus: AnnotationFocus
    conceptual_references: List[str]
    persona_voice: str


class FinalPersona(BaseModel):
    name: str
    based_on_raw_author: str
    generated_at: str
    core_identity: dict
    methodological_profile: MethodologicalProfile
    domain_focus_weights: DomainWeights
    communication_style: CommunicationStyle
    evaluation_style: EvaluationStyle
    annotation_focus: AnnotationFocus
    annotation_rules: List[str]
    conceptual_references: List[str]
    persona_voice: str
    inference_summary: str  # Compact summary for inference time — Generative Agents, Appendix A


# ==========================================
# PROMPT DEFINITIONS
# ==========================================

# Technique: Extractive Summarization & Grounding Constraints
# + Objective/Subjective split (PersLLM, Section 3.1)
STAGE1_SYSTEM = """
You are an expert in Software Engineering research analysis.
Analyze this batch of publications from a single author.

IMPORTANT — distinguish between two types of signals:
- knowledge_signals: The TOPICS and DOMAINS the author studies (what they know about)
- style_signals: HOW the author reasons and argues — empirical vs theoretical preference,
  confidence level in claims, what kinds of evidence they rely on, argumentation patterns

If an abstract is missing or minimal, extract only from title and venue.

CRITICAL RULES:
- Do NOT invent or guess missing information.
- Ground everything strictly in the provided paper data.
"""

# Technique: Zero-Shot Classification & Pattern Synthesis
STAGE2_SYSTEM = """
You are an expert in distilling Software Engineering research patterns into factual researcher profiles.
Combine the provided chunk summaries into a single, holistic research identity.

Pay special attention to knowledge_signals and style_signals across chunks
when building communication_indicators — these are the most direct evidence of behavioral style.

CRITICAL RULES:
- Do NOT add new research areas not present in the chunks.
- Mark weak patterns as uncertain.
- Where chunks disagree, surface both views rather than picking one.
"""

# Technique: Reflection — Generative Agents, Section 4.2
# Bridges "what they study" to "how they evaluate code quality tasks"
STAGE25_SYSTEM = """
You are an expert in behavioral inference for Software Engineering researchers.
Given a researcher's publication profile, generate HIGH-LEVEL BEHAVIORAL INSIGHTS
that explain how their research background would shape their JUDGMENT when evaluating code quality tasks.

Do NOT describe what they study. INFER how their background would make them EVALUATE,
PRIORITIZE, and LABEL software issues differently from a generic evaluator.

For each insight, cite the specific research evidence that supports it.

CRITICAL RULES:
- Every behavioral insight must be grounded in specific research evidence.
- Focus on evaluation behavior, not research description.
"""

# Technique: Explicit Chain-of-Thought (CoT) Forcing
# CoT must reference reflection insights, not just raw topics
STAGE3_SYSTEM = """
You are an expert in modeling Software Engineering researcher behavior.
Transform the provided global research profile AND behavioral reflection insights
into structured persona features.

CRITICAL RULES:
- Your reasoning_process MUST explicitly reference the behavioral_insights
  and evaluation_approach from the reflection — not just restate research topics.
- Domain weights must align with the reflection's evaluation_approach.
"""


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def extract_author_context(raw_author: dict) -> dict:
    """
    Extract metadata from raw_data that the original pipeline ignores:
    declared interests, co-authors, h-index, total citations.
    """
    context = {}
    raw_data = raw_author.get("raw_data", {})
    profile = raw_data.get("serpapi_profile_response", {}).get("author", {})

    interests = profile.get("interests", [])
    context["declared_interests"] = [i.get("title", "") for i in interests if i.get("title")]

    co_authors = raw_data.get("serpapi_profile_response", {}).get("co_authors", [])
    context["co_authors"] = [ca.get("name", "") for ca in co_authors if ca.get("name")]

    cited_by = profile.get("cited_by", {})
    table = cited_by.get("table", [])
    context["total_citations"] = table[0].get("citations", {}).get("all", 0) if table else 0

    h_index_entry = next((t for t in table if "h_index" in t), {})
    context["h_index"] = h_index_entry.get("h_index", {}).get("all", 0)

    return context


def chunk_papers(papers: list, chunk_size: int = CHUNK_SIZE) -> list:
    """Split papers into chunks to prevent Lost in the Middle degradation."""
    return [papers[i:i + chunk_size] for i in range(0, len(papers), chunk_size)]


def build_annotation_rules(features: dict, reflection: dict) -> List[str]:
    """
    Deterministically build annotation rules from features and reflection output.
    """
    rules = []

    annotation_focus = features.get("annotation_focus", {})
    for concern in annotation_focus.get("primary_concerns", []):
        rules.append(f"Prioritize issues related to: {concern}")

    eval_approach = reflection.get("evaluation_approach", "")
    if eval_approach:
        rules.append(f"Overall evaluation approach: {eval_approach}")

    return rules


def build_inference_summary(
    author_name: str,
    raw_author: dict,
    profile: dict,
    features: dict,
    reflection: dict
) -> str:
    """
    Compact inference-time identity string — Generative Agents, Appendix A.
    Replaces the full FinalPersona JSON as the system prompt at inference time,
    preventing Lost in the Middle degradation when the persona answers survey tasks.
    """
    primary_themes = ", ".join(profile.get("primary_research_themes", [])[:3])
    eval_approach = reflection.get("evaluation_approach", "")
    voice = features.get("persona_voice", "")
    tone = features.get("communication_style", {}).get("tone", "")
    limitations = "; ".join(features.get("evaluation_style", {}).get("limitations", [])[:2])
    affiliation = raw_author.get("affiliation", "")

    summary = (
        f"{author_name} is a Software Engineering researcher at {affiliation}, "
        f"focused on {primary_themes}. "
        f"Evaluation approach: {eval_approach} "
        f"Communication style: {tone}. "
        f"Known limitations: {limitations}. "
        f"Voice: {voice}"
    )
    return summary.strip()


# ==========================================
# PIPELINE EXECUTION
# Technique: Prompt Chaining (Modular LLM Architecture)
# ==========================================

def generate_persona_from_raw(raw_author: dict, author_name: str, raw_filename: str) -> dict:
    llm = LLMClient()

    # Papers are already domain-filtered by scraping_service before reaching this pipeline
    papers = raw_author.get("papers", [])

    # --- Pre-processing ---
    author_context = extract_author_context(raw_author)

    # No importance weighting — papers passed directly to chunking
    paper_chunks = chunk_papers(papers, CHUNK_SIZE)

    # --- Stage 1: Chunked Extraction ---
    # Extractive Summarization & Grounding Constraints
    # + Objective/Subjective split (PersLLM, Section 3.1)
    chunks = []
    for i, chunk in enumerate(paper_chunks):
        s1_prompt = (
            f"Author declared research interests: {author_context['declared_interests']}\n\n"
            f"Analyze these papers (chunk {i + 1} of {len(paper_chunks)}):\n"
            f"{json.dumps(chunk, ensure_ascii=False)}"
        )
        summary = llm.generate_structured(STAGE1_SYSTEM, s1_prompt, Stage1Summary)
        summary["chunk_id"] = i
        chunks.append(summary)

    # --- Stage 2: Global Profile Synthesis ---
    # Zero-Shot Classification & Pattern Synthesis
    s2_prompt = (
        f"Author context (declared interests, co-authors, citation impact):\n"
        f"{json.dumps(author_context, ensure_ascii=False)}\n\n"
        f"Synthesize these {len(chunks)} chunk summaries into a unified research profile:\n"
        f"{json.dumps(chunks, ensure_ascii=False)}"
    )
    profile = llm.generate_structured(STAGE2_SYSTEM, s2_prompt, Stage2Profile)

    # --- Stage 2.5: Behavioral Reflection ---
    # Generative Agents, Section 4.2
    # Bridges "what they study" → "how they evaluate code quality"
    s25_prompt = (
        f"Researcher: {author_name}\n"
        f"Affiliation: {raw_author.get('affiliation', 'Unknown')}\n"
        f"Declared interests: {author_context['declared_interests']}\n"
        f"h-index: {author_context.get('h_index', 'Unknown')}\n\n"
        f"Research profile:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
        f"Generate high-level behavioral insights about how this researcher would approach "
        f"code quality evaluation and labeling tasks. Do not describe their research — "
        f"infer their evaluation behavior."
    )
    reflection = llm.generate_structured(STAGE25_SYSTEM, s25_prompt, Stage25Reflection)

    # --- Stage 3: Behavioral Synthesis with CoT ---
    # Explicit Chain-of-Thought Forcing
    # CoT grounded in reflection insights, not just raw profile
    s3_prompt = (
        f"Research profile:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
        f"Behavioral reflection insights:\n{json.dumps(reflection, ensure_ascii=False)}\n\n"
        f"Generate structured persona features. Your reasoning_process must explicitly "
        f"reference the behavioral_insights and evaluation_approach from the reflection."
    )
    features = llm.generate_structured(STAGE3_SYSTEM, s3_prompt, Stage3Features)

    # --- Stage 4: Deterministic Assembly ---
    # Context Merging & Structured Assembly
    # Pure Python dict merge — no LLM call needed for mechanical assembly
    annotation_rules = build_annotation_rules(features, reflection)
    inference_summary = build_inference_summary(
        author_name, raw_author, profile, features, reflection
    )

    persona = {
        "name": author_name,
        "based_on_raw_author": raw_filename,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "core_identity": {
            "summary": profile.get("researcher_summary", ""),
            "academic_orientation": raw_author.get("affiliation", ""),
            "primary_research_themes": profile.get("primary_research_themes", []),
            "secondary_research_themes": profile.get("secondary_research_themes", []),
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

    return persona
