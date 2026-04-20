import os
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==========================================
# CONFIGURATION: CONTEXTUAL INTENT CLUSTERING
# ==========================================
RESEARCHERS = [
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
    # Alireza is commented out because his ground-truth data is line-by-line, not clustered.
]

# ---------------------------------------------------------------------------
# SCHEMA DEFINITIONS
# ---------------------------------------------------------------------------
class LabelCategories(BaseModel):
    bugfix: list[int] = Field(description="Line indices for bugfixes. [] if none.")
    whitespace: list[int] = Field(description="Line indices for pure, unrelated whitespace. [] if none.")
    documentation: list[int] = Field(description="Line indices for pure, unrelated documentation. [] if none.")
    refactoring: list[int] = Field(description="Line indices for refactoring. [] if none.")
    test: list[int] = Field(description="Line indices for tests. [] if none.")
    unrelated: list[int] = Field(description="Line indices for unrelated changes. [] if none.")

class HunkAnnotation(BaseModel):
    hunk_number: int = Field(description="The index of the hunk being evaluated.")
    primary_intent: str = Field(description="What is the single overarching purpose of this entire block of code?")
    cluster_reasoning: str = Field(description="Using your Persona, explain how all lines in this block support the primary intent.")
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
# THE PIPELINE
# ---------------------------------------------------------------------------
def run_pipeline():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "A"))
    BATCH_SIZE = 5

    for researcher in RESEARCHERS:
        print(f"\n==================================================")
        print(f" 📦 STARTING CLUSTER ANNOTATION FOR: {researcher['name']} 📦 ")
        print(f"==================================================")

        try:
            with open(researcher['persona_file'], 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
            with open(researcher['context_file'], 'r', encoding='utf-8') as f:
                all_hunks = json.load(f)
        except FileNotFoundError as e:
            print(f"[!] Missing file: {e}. Skipping.")
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

YOUR ANNOTATION PROTOCOL: CLUSTER COHESION
You must evaluate code blocks based on their OVERALL INTENT, rather than fracturing them line-by-line. 

CRITICAL RULES:
1. IDENTIFY THE PRIMARY INTENT: Look at the entire hunk. Is the developer primarily fixing a bug, writing a test, or refactoring?
2. DO NOT FRAGMENT THE CLUSTER: If the primary intent of the block is a `bugfix`, then any blank lines, brackets, or comments added *inside that block* exist to support the bugfix. They MUST be labeled as `bugfix`. Do not isolate them into `whitespace` or `documentation`.
3. ISOLATE ONLY TRUE TANGLES: You should only use multiple categories in a single hunk if the developer is clearly doing two completely unrelated things at the same time (e.g., fixing a bug at the top of the hunk, and formatting an unrelated method at the bottom).

Use your Persona to determine the primary intent of the block, then assign the lines to that cluster.
"""
            prompt = f"Evaluate the following code hunks sequentially using the Cluster Cohesion Protocol:\n{hunks_payload}"
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