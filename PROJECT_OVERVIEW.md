# Consensia: Project Overview & Technical Documentation

## Project Goal

**Consensia** is a research project exploring whether a large language model (LLM) can act as a trustworthy judge by orchestrating multiple expert personas to reach an explainable consensus. The system allows users to define AI personas with different backgrounds/expertise, pose questions, and receive both individual persona responses and a synthesized judge consensus.

---

## Architecture Overview

### Technology Stack

**Frontend:**
- React 18 with TypeScript
- Vite for build tooling and dev server
- Tailwind CSS for styling (purple/black theme)
- Modular component architecture

**Backend:**
- FastAPI (Python 3.11+)
- Async/await for concurrent LLM calls
- Support for multiple LLM providers (OpenAI, Google Gemini)
- Pydantic for request/response validation

**LLM Integration:**
- Primary: Google Gemini 2.0 Flash (free tier)
- Fallback: OpenAI GPT-4o-mini
- Simulated responses when no API keys are present (for UI development)

---

## How the LLM System Works

### 1. Persona Answer Generation

**Location:** `backend/app/services/llm.py` - `generate_persona_answer()`

**Process:**
1. For each persona defined by the user, the system creates an **independent LLM chat session**
2. Each persona receives a **system instruction** that includes:
   - The persona's name
   - The persona's background/description
   - Instructions to role-play as that character, adopting their tone, priorities, and expertise level
3. The user's question is sent as the user message
4. The LLM generates a response **in character** for that persona
5. All persona calls run **concurrently** using `asyncio.gather()` for efficiency

**Key Code:**
```python
# System instruction for each persona (lines 218-225)
def _build_persona_instruction(self, persona: Persona) -> str:
    return (
        "You are an AI agent participating in a structured debate.\n"
        f"Your persona name: {persona.name}\n"
        f"Persona background: {persona.description}\n"
        "Role-play this character faithfully, adopt their tone, priorities, and level of expertise.\n"
        "Keep the response concise (3-6 sentences) unless deeper analysis is required."
    )
```

**Example:**
- Persona: "Junior Software Engineer - 1 year experience, recently graduated, focuses on quick solutions"
- Question: "Should we use microservices or monolith architecture?"
- The LLM responds as a junior engineer would: practical, quick-to-implement solutions, less concern for long-term scalability

### 2. Judge Consensus Generation

**Location:** `backend/app/services/llm.py` - `generate_judge_consensus()`

**Process:**
1. After all persona answers are collected, a **separate LLM chat session** is created for the judge
2. The judge receives:
   - The original question
   - All persona responses, **including each persona's name and background** (so the judge understands who said what and why)
   - Instructions to synthesize a consensus and provide reasoning
3. The judge is instructed to return structured JSON with:
   - `summary`: A concise consensus answer
   - `reasoning`: Explanation that references the personas' points and backgrounds
4. The judge uses a **lower temperature (0.4)** for more deterministic, analytical responses

**Key Code:**
```python
# Judge system instruction (lines 141-146)
"You are an impartial judge. Read the persona responses and deliver:\n"
"1. A concise summary that captures the best consensus.\n"
"2. A reasoning section that references the personas' points.\n"
"Return JSON with keys 'summary' and 'reasoning'."
```

**Context Building:**
```python
# Judge receives full persona context (lines 235-245)
def _build_judge_context(self, persona_answers: Iterable[PersonaAnswer]) -> str:
    sections = []
    for answer in persona_answers:
        sections.append(
            f"Persona ID: {answer.persona_id}\n"
            f"Persona Name: {answer.persona_name}\n"
            f"Persona Background: {answer.persona_description}\n"
            f"Response:\n{answer.answer}"
        )
    return "\n\n".join(sections)
```

### 3. API Endpoint Flow

**Location:** `backend/app/main.py` - `generate_consensus()`

**Request Flow:**
1. Frontend sends POST to `/api/consensus` with:
   - Question string
   - Array of personas (id, name, description)

2. Backend validates input (at least one persona required)

3. **Concurrent persona generation:**
   ```python
   persona_answers = await asyncio.gather(
       *(service.generate_persona_answer(persona, payload.question) 
         for persona in payload.personas)
   )
   ```

4. **Sequential judge generation** (waits for all personas):
   ```python
   judge_consensus = await service.generate_judge_consensus(
       persona_answers, payload.question
   )
   ```

5. Response includes:
   - Array of persona answers (with persona metadata)
   - Judge consensus (summary + reasoning)

---

## LLM Provider Abstraction

**Location:** `backend/app/services/llm.py` - `LLMService` class

**Design Decision:** The system supports multiple LLM providers through a unified interface:

1. **Provider Resolution** (lines 42-54):
   - Checks environment variable `LLM_PROVIDER` (auto/openai/gemini)
   - Auto mode: Prefers OpenAI if key exists, otherwise Gemini, otherwise simulated

2. **Unified Methods:**
   - `generate_persona_answer()` - Routes to provider-specific implementation
   - `generate_judge_consensus()` - Routes to provider-specific implementation

3. **Provider-Specific Implementations:**
   - `_generate_persona_answer_openai()` / `_generate_persona_answer_gemini()`
   - `_generate_judge_consensus_openai()` / `_generate_judge_consensus_gemini()`

4. **Fallback:** If no API keys are present, simulated responses are returned (allows UI development without API costs)

**Why This Design:**
- Flexibility to switch providers based on cost/availability
- Easy to add new providers (Anthropic, etc.)
- Development can continue without API keys

---

## Development Process & Decisions

### 1. **Why React + FastAPI Split?**
- **Separation of concerns:** Frontend handles UI/UX, backend handles LLM orchestration
- **Team flexibility:** Frontend and backend can be developed independently
- **Future scalability:** Can deploy frontend/backend separately, add mobile apps, etc.

### 2. **Why Async/Await?**
- **Performance:** Persona calls run concurrently, not sequentially
- **Efficiency:** With 3 personas, concurrent calls take ~same time as 1 call (vs 3x sequential)
- **Scalability:** Can handle many personas without linear time increase

### 3. **Why Separate Judge Session?**
- **Isolation:** Judge doesn't see other persona's "thinking process" - only final answers
- **Fairness:** Each persona gets equal weight in the judge's analysis
- **Transparency:** Judge reasoning can reference specific personas by name/background

### 4. **Why Include Persona Backgrounds in Judge Context?**
- **Context-aware reasoning:** Judge understands *why* a junior engineer might prioritize speed vs. a senior engineer prioritizing scalability
- **Better synthesis:** Judge can reconcile conflicting viewpoints by understanding the personas' perspectives
- **Explainability:** Judge reasoning can reference persona expertise levels

### 5. **Temperature Settings:**
- **Personas (0.7):** Higher creativity/variation to capture different personality styles
- **Judge (0.4):** Lower temperature for more analytical, consistent consensus

---

## Current Limitations & Future Work

### Current State (MVP):
- ✅ Multiple personas with custom backgrounds
- ✅ Concurrent persona answer generation
- ✅ Judge consensus with reasoning
- ✅ Support for OpenAI and Gemini
- ✅ Modern React UI with purple/black theme

### Planned Enhancements:
1. **Persona Memory:** Upload CVs/resumes to create more detailed personas
2. **Debate History:** Track conversations over time, persona consistency
3. **Advanced Judge Features:** Confidence scores, structured rationales, citation tracking
4. **Persona Traits:** More granular control (communication style, risk tolerance, etc.)
5. **Streaming Responses:** Real-time persona answers as they generate
6. **Persona Interaction:** Allow personas to see and respond to each other's answers

---

## Key Files Reference

- **Backend LLM Logic:** `backend/app/services/llm.py`
- **API Endpoints:** `backend/app/main.py`
- **Request/Response Schemas:** `backend/app/schemas.py`
- **Configuration:** `backend/app/config.py`
- **Frontend Main App:** `frontend/src/App.tsx`
- **Frontend Components:** `frontend/src/components/`

---

## Running the Project

See `README.md` for detailed setup instructions. Quick start:

**Backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# Create .env file with GEMINI_API_KEY or OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to use the application.

---

## Research Questions

This project explores:
1. Can LLMs reliably role-play distinct personas with different expertise levels?
2. Can an LLM judge synthesize multiple perspectives into a coherent consensus?
3. How does including persona backgrounds affect judge reasoning quality?
4. What are the limitations of LLM-based consensus generation?

---


