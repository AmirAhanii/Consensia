from typing import List, Dict, Any
import json
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.llm_client import LLMClient

# ==========================================
# PYDANTIC SCHEMAS (STRUCTURED OUTPUTS)
# Technique: Constrained Decoding / Schema Enforcement
# Paper Context: By defining strict Pydantic models, we bypass standard text generation 
# and force the LLM's decoding process to only emit tokens that form valid JSON 
# matching these exact data types. This guarantees zero parsing errors.
# ==========================================

class Stage1Summary(BaseModel):
    chunk_id: int
    primary_themes: List[str]
    secondary_themes: List[str]
    methodologies: List[str]
    recurring_concepts: List[str]
    summary: str

class Stage2Profile(BaseModel):
    primary_research_themes: List[str]
    secondary_research_themes: List[str]
    methodological_traits: List[str]
    recurring_concepts: List[str]
    communication_indicators: List[str]
    researcher_summary: str

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

class EvaluationStyle(BaseModel):
    decision_making_traits: List[str]
    biases: List[str]
    limitations: List[str]

class AnnotationFocus(BaseModel):
    primary_concerns: List[str]
    secondary_concerns: List[str]
    quality_indicators: List[str]

class Stage3Features(BaseModel):
    # Technique: Chain-of-Thought (CoT) Prompting via Schema Design
    # Paper Context: Placing the reasoning process BEFORE the weights forces the LLM 
    # to compute its logic step-by-step prior to tokenizing the final output values.
    reasoning_process: str = Field(description="Step-by-step logic justifying these features based strictly on the profile.")
    domain_focus_weights: DomainWeights
    methodological_profile: MethodologicalProfile
    communication_style: CommunicationStyle
    evaluation_style: EvaluationStyle
    annotation_focus: AnnotationFocus
    conceptual_references: List[str]
    persona_voice: str

class Stage4PersonaCore(BaseModel):
    summary: str
    academic_orientation: str
    primary_research_themes: List[str]
    secondary_research_themes: List[str]

class FinalPersona(BaseModel):
    name: str
    based_on_raw_author: str
    generated_at: str
    core_identity: Stage4PersonaCore
    methodological_profile: MethodologicalProfile
    domain_focus_weights: DomainWeights
    communication_style: CommunicationStyle
    evaluation_style: EvaluationStyle
    annotation_focus: AnnotationFocus
    annotation_rules: List[str]
    conceptual_references: List[str]
    persona_voice: str


# ==========================================
# PROMPT DEFINITIONS
# ==========================================

# Technique: Extractive Summarization & Grounding Constraints
# Paper Context: This stage acts as a data dimensionality reduction step. We use strict 
# grounding constraints ("Do NOT invent") to extract only explicitly stated themes.
STAGE1_SYSTEM = """
You are an expert in Software Engineering research analysis.
Analyze this batch of publications from a single author.
Extract recurring themes, methodologies, and concepts visible in the metadata and abstracts.
CRITICAL RULES:
- Do NOT invent or guess missing information.
- Ground everything strictly in the provided paper list.
"""

# Technique: Zero-Shot Classification & Pattern Synthesis
# Paper Context: The model is asked to classify and synthesize the previously extracted 
# chunks without prior examples (Zero-Shot), merging them into a unified profile.
STAGE2_SYSTEM = """
You are an expert in distilling Software Engineering research patterns into factual researcher profiles.
Combine the provided chunk summaries into a single, holistic research identity.
CRITICAL RULES:
- Do NOT add new research areas not present in the chunks.
- Mark weak patterns as uncertain.
"""

# Technique: Explicit Chain-of-Thought (CoT) Forcing
# Paper Context: We mandate that the LLM generates a rationale prior to assigning 
# behavioral traits, drastically reducing hallucination of personality parameters.
STAGE3_SYSTEM = """
You are an expert in modeling Software Engineering researcher behavior.
Transform the provided global research profile into structured persona features.
CRITICAL RULE:
You must write out your `reasoning_process` step-by-step before assigning the weights and features. Explain exactly why their publication history leads to this specific communication style and domain focus.
"""

# Technique: Context Merging & Structured Assembly
# Paper Context: Final determinisitic assembly of the data structures into the master schema.
STAGE4_SYSTEM = """
You are an expert persona assembler.
Combine the metadata, global research profile, and persona features into the final unified persona format.
Do not invent any new characteristics.
"""

# ==========================================
# PIPELINE EXECUTION
# Technique: Prompt Chaining (Modular LLM Architecture)
# Paper Context: By chaining multiple isolated LLM calls, we bypass the "Lost in the Middle" 
# context-window limitation and isolate cognitive tasks (Extraction -> Synthesis -> Formatting).
# ==========================================

def generate_persona_from_raw(raw_author: dict, author_name: str, raw_filename: str) -> dict:
    llm = LLMClient()
    papers = raw_author.get("papers", [])

    # --- Stage 1: Extraction ---
    s1_prompt = f"Analyze these papers:\n{json.dumps(papers, ensure_ascii=False)}"
    chunk = llm.generate_structured(STAGE1_SYSTEM, s1_prompt, Stage1Summary)
    chunks = [chunk] 

    # --- Stage 2: Global Profile ---
    s2_prompt = f"Combine these summaries:\n{json.dumps(chunks, ensure_ascii=False)}"
    profile = llm.generate_structured(STAGE2_SYSTEM, s2_prompt, Stage2Profile)

    # --- Stage 3: Behavioral Synthesis (with Chain of Thought) ---
    s3_prompt = f"Generate behavioral features from this profile:\n{json.dumps(profile, ensure_ascii=False)}"
    features = llm.generate_structured(STAGE3_SYSTEM, s3_prompt, Stage3Features)

    # --- Stage 4: Assembly ---
    meta = {
        "name": author_name,
        "based_on_raw_author": raw_filename,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    
    s4_prompt = f"""
    Metadata: {json.dumps(meta, ensure_ascii=False)}
    Profile: {json.dumps(profile, ensure_ascii=False)}
    Features: {json.dumps(features, ensure_ascii=False)}
    """
    persona = llm.generate_structured(STAGE4_SYSTEM, s4_prompt, FinalPersona)
    
    return persona