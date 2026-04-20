import os
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==========================================
# CONFIGURATION: FULL DATASET BASELINE
# ==========================================
RESEARCHERS = [
    {
        "name": "Alireza Aghamohammadi",
        "context_file": "aaghamohammadi_only_context.json",
        "output_file": "aaghamohammadi_full_baseline_results.json"
    },
    {
        "name": "Alexander Trautsch",
        "context_file": "atrautsch_only_context.json",
        "output_file": "atrautsch_full_baseline_results.json"
    },
    {
        "name": "Steffen Herbold",
        "context_file": "sherbold_only_context.json",
        "output_file": "sherbold_full_baseline_results.json"
    }
]

# ---------------------------------------------------------------------------
# SCHEMA DEFINITIONS
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
    reasoning: str = Field(description="Step-by-step logic identifying the labels based on standard software engineering principles.")
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
# THE FULL BASELINE PIPELINE
# ---------------------------------------------------------------------------
def run_pipeline():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "A"))
    BATCH_SIZE = 5

    for researcher in RESEARCHERS:
        print(f"\n==================================================")
        print(f" 🧪 STARTING FULL BASELINE FOR: {researcher['name']} 🧪 ")
        print(f"==================================================")

        try:
            with open(researcher['context_file'], 'r', encoding='utf-8') as f:
                all_hunks = json.load(f)
        except FileNotFoundError as e:
            print(f"[!] Missing file: {e}. Skipping.")
            continue

        # Pure, unguided system instruction (No Persona)
        system_instruction = """
You are an expert scientific code annotator identifying "tangled commits".
Your task is to classify numbered lines of code diffs into standard categories.

THE TASK:
Classify the following new numbered lines into the provided JSON categories.

CRITICAL RULES:
- Isolate the true bugfix from unrelated noise or refactorings based on standard software engineering logic.
- If a category does not apply to any lines, output an empty array [].
"""
        
        total_hunks = len(all_hunks)
        all_results = []
        print(f"[*] Found {total_hunks} total hunks. Processing in batches of {BATCH_SIZE}...")

        for i in range(0, total_hunks, BATCH_SIZE):
            batch_hunks = all_hunks[i : i + BATCH_SIZE]
            
            hunks_payload = ""
            for idx, hunk in enumerate(batch_hunks):
                # Standard numbering starting from 1
                real_hunk_num = i + idx + 1
                numbered_diff = format_diff_with_line_numbers(hunk['context_code'])
                hunks_payload += f"\n=== HUNK NUMBER {real_hunk_num} ===\nPROJECT: {hunk.get('project', 'Unknown')}\nCODE DIFF:\n{numbered_diff}\n"

            prompt = f"Evaluate these code hunks sequentially:\n{hunks_payload}"
            
            current_end = min(i + BATCH_SIZE, total_hunks)
            print(f"    -> Predicting Hunks {i + 1} to {current_end}... ", end="", flush=True)

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
                print(f"\n[!] ERROR: {e}")
                print("[!] Skipping this batch and cooling down...")
                time.sleep(5)

        print(f"[SUCCESS] Finished {researcher['name']}. Saved to {researcher['output_file']}\n")

if __name__ == "__main__":
    run_pipeline()