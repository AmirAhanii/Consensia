import os
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==========================================
# CONFIGURATION: HIERARCHY PROTOCOL (CODEBOOK + PERSONA)
# ==========================================
RESEARCHERS = [
    {
        "name": "Alireza Aghamohammadi",
        "persona_file": "persona_alireza_aghamohammadi_v1.json",
        "context_file": "aaghamohammadi_only_context.json",
        "output_file": "aaghamohammadi_api_results.json"
    },
    {
        "name": "Alexander Trautsch",
        "persona_file": "persona_alexander_trautsch_v1.json",
        "context_file": "atrautsch_only_context.json",
        "output_file": "atrautsch_api_results.json"
    },
    {
        "name": "Steffen Herbold",
        "persona_file": "persona_steffen_herbold_v1.json",
        "context_file": "sherbold_only_context.json",
        "output_file": "sherbold_api_results.json"
    }
]

# ---------------------------------------------------------------------------
# SCHEMA DEFINITIONS (The 2-Speed Brain)
# ---------------------------------------------------------------------------
class LabelCategories(BaseModel):
    bugfix: list[int] = Field(description="Line indices that are part of the bugfix. [] if none.")
    whitespace: list[int] = Field(description="Line indices that are whitespace. [] if none.")
    documentation: list[int] = Field(description="Line indices that are documentation. [] if none.")
    refactoring: list[int] = Field(description="Line indices that are refactoring. [] if none.")
    test: list[int] = Field(description="Line indices that are tests. [] if none.")
    unrelated: list[int] = Field(description="Line indices that are unrelated. [] if none.")

class HunkAnnotation(BaseModel):
    hunk_number: int = Field(description="The index of the hunk being evaluated.")
    objective_filter_check: str = Field(description="Step 1: Check the Codebook. Quickly identify any obvious lines that belong in 'test', 'whitespace', or 'unrelated'. Do not overthink these.")
    subjective_persona_evaluation: str = Field(description="Step 2: For complex logic that bypassed the filter, activate your Persona. Debate 'bugfix' vs 'refactoring' strictly using your academic biases.")
    labels: LabelCategories

class BatchAnnotationResult(BaseModel):
    results: list[HunkAnnotation]

def format_diff_with_line_numbers(diff_string: str) -> str:
    lines = diff_string.split('\n')
    formatted_lines = []
    changed_line_index = 0
    for line in lines:
        if line.startswith('+') or line.startswith('-'):
            formatted_lines.append(f"Line {changed_line_index}: {line}")
            changed_line_index += 1
        else:
            formatted_lines.append(f"        {line}") 
    return '\n'.join(formatted_lines)

# ---------------------------------------------------------------------------
# THE HIERARCHY PIPELINE
# ---------------------------------------------------------------------------
def run_pipeline():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "A"))
    BATCH_SIZE = 5

    for researcher in RESEARCHERS:
        print(f"\n==================================================")
        print(f" 👑 STARTING HIERARCHY ANNOTATION FOR: {researcher['name']} 👑 ")
        print(f"==================================================")

        try:
            with open(researcher['persona_file'], 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
        except FileNotFoundError:
            print(f"[!] Persona file not found: {researcher['persona_file']}. Skipping.")
            continue
            
        try:
            with open(researcher['context_file'], 'r', encoding='utf-8') as f:
                all_hunks = json.load(f)
        except FileNotFoundError:
            print(f"[!] Context file not found: {researcher['context_file']}. Skipping.")
            continue

        total_hunks = len(all_hunks)
        all_results = []

        print(f"[*] Found {total_hunks} hunks. Processing in batches of {BATCH_SIZE}...")

        for i in range(0, total_hunks, BATCH_SIZE):
            batch_hunks = all_hunks[i : i + BATCH_SIZE]
            
            hunks_payload = ""
            for idx, hunk in enumerate(batch_hunks, start=i+1):
                numbered_diff = format_diff_with_line_numbers(hunk['context_code'])
                hunks_payload += f"\n=== HUNK NUMBER {idx} ===\nPROJECT: {hunk.get('project', 'Unknown')}\nFILE: {hunk.get('file_name', 'Unknown')}\nCODE DIFF:\n{numbered_diff}\n"

            system_instruction = f"""
You are participating in a scientific code annotation task.
Your internal identity is strictly defined by this Persona JSON:
{json.dumps(persona_data, indent=2)}

YOUR ANNOTATION PROTOCOL:
When evaluating these numbered code diffs, you MUST follow a strict 2-step hierarchy.

STEP 1: THE OBJECTIVE FILTER (The Codebook)
First, quickly filter out trivial logistics. If a line meets these exact conditions, label it immediately and DO NOT apply your persona to it:
- `test`: Modifies an `assert` statement, or is located inside a test file/suite.
- `whitespace`: Only adds, removes, or modifies empty spaces, tabs, or blank newlines.
- `unrelated`: Modifies configuration files (e.g., .gitignore, pom.xml), dependency versions, or licenses outside core logic.

STEP 2: THE SUBJECTIVE EVALUATION (Your Persona)
For all core logic changes that pass through the filter, the Codebook no longer applies. You must now rely ENTIRELY on your Persona.
- Is this complex logic a `bugfix` or a `refactoring`? 
- Use your specific empirical rigor, biases, and methodological traits to debate and decide.

If a category does not apply to any lines, output an empty array [].
"""
            prompt = f"Evaluate the following code hunks sequentially using the 2-Step Hierarchy Protocol:\n{hunks_payload}"
            current_end = min(i + BATCH_SIZE, total_hunks)
            print(f"    -> Predicting Hunks {i+1} to {current_end}... ", end="", flush=True)

            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=BatchAnnotationResult,
                        temperature=0.1 
                    ),
                )

                batch_result_dict = json.loads(response.text)
                all_results.extend(batch_result_dict.get("results", []))
                
                with open(researcher['output_file'], 'w', encoding='utf-8') as f:
                    json.dump({"results": all_results}, f, indent=2)
                    
                print("Done! (Auto-saved)")
                time.sleep(1) 

            except Exception as e:
                print(f"\n[!] ERROR on Hunks {i+1}-{current_end}: {e}")
                print("[!] Skipping this batch and cooling down...")
                time.sleep(5)

        print(f"[SUCCESS] Finished {researcher['name']}. Saved to {researcher['output_file']}\n")

if __name__ == "__main__":
    run_pipeline()