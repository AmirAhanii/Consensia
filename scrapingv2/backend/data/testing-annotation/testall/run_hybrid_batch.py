import os
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==========================================
# CONFIGURATION: THE HYBRID SETUP
# ==========================================
RESEARCHERS = [
    {
        "name": "Alireza Aghamohammadi",
        "persona_file": "persona_alireza_aghamohammadi_v1.json",
        "train_file": "aaghamohammadi_train.json",
        "test_file": "aaghamohammadi_test.json",
        "truth_key": "aaghamohammadi", 
        "output_file": "aaghamohammadi_hybrid_results.json"
    },
    {
        "name": "Alexander Trautsch",
        "persona_file": "persona_alexander_trautsch_v1.json",
        "train_file": "atrautsch_train.json",
        "test_file": "atrautsch_test.json",
        "truth_key": "atrautsch",
        "output_file": "atrautsch_hybrid_results.json"
    },
    {
        "name": "Steffen Herbold",
        "persona_file": "persona_steffen_herbold_v1.json",
        "train_file": "sherbold_train.json",
        "test_file": "sherbold_test.json",
        "truth_key": "sherbold",
        "output_file": "sherbold_hybrid_results.json"
    }
]

MAX_FEW_SHOT_EXAMPLES = 30 

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
    persona_lens: str = Field(description="A brief statement in the persona's voice explaining their priority.")
    reasoning: str = Field(description="Step-by-step logic applying your persona biases to the code patterns.")
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
# THE HYBRID PIPELINE
# ---------------------------------------------------------------------------
def run_pipeline():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "A"))
    BATCH_SIZE = 5

    for researcher in RESEARCHERS:
        print(f"\n==================================================")
        print(f" 🧬 STARTING HYBRID PIPELINE FOR: {researcher['name']} 🧬 ")
        print(f"==================================================")

        # 1. Load Persona, Training, and Testing Data
        try:
            with open(researcher['persona_file'], 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
            with open(researcher['train_file'], 'r', encoding='utf-8') as f:
                train_data = json.load(f)
            with open(researcher['test_file'], 'r', encoding='utf-8') as f:
                test_data = json.load(f)
        except FileNotFoundError as e:
            print(f"[!] Missing file: {e}. Skipping.")
            continue

        # 2. Build the Few-Shot Examples String
        print(f"[*] Building Historical Examples from {researcher['train_file']}...")
        examples_string = ""
        example_count = min(len(train_data), MAX_FEW_SHOT_EXAMPLES)
        
        for i in range(example_count):
            hunk = train_data[i]
            numbered_diff = format_diff_with_line_numbers(hunk['context_code'])
            
            truth_str = hunk.get(researcher['truth_key'], '{}')
            try:
                truth_json = json.dumps(json.loads(truth_str), indent=2)
            except:
                truth_json = "{}"

            examples_string += f"\n--- PAST ANNOTATION {i+1} ---\nCODE DIFF:\n{numbered_diff}\nYOUR HISTORICAL LABELS:\n{truth_json}\n"

        # 3. Create the Hybrid System Instruction (Persona + Examples)
        system_instruction = f"""
You are participating in a scientific code annotation task to identify "tangled commits".
Adopt the following persona completely based on this JSON definition:
{json.dumps(persona_data, indent=2)}

To calibrate your judgment, here are examples of how YOU have historically evaluated code:
### YOUR PAST ANNOTATIONS:
{examples_string}

THE TASK:
Classify the following new numbered lines into the provided JSON categories.

CRITICAL RULES:
- Isolate the true bugfix from unrelated noise based strictly on your persona's biases AND the patterns established in your past annotations.
- If a category does not apply to any lines, output an empty array [].
"""
        
        total_test_hunks = len(test_data)
        all_results = []
        print(f"[*] Found {total_test_hunks} testing hunks. Processing in batches of {BATCH_SIZE}...")

        # 4. Batch Process the 20% Testing Set
        for i in range(0, total_test_hunks, BATCH_SIZE):
            batch_hunks = test_data[i : i + BATCH_SIZE]
            
            hunks_payload = ""
            for idx, hunk in enumerate(batch_hunks):
                real_hunk_num = len(train_data) + i + idx + 1
                numbered_diff = format_diff_with_line_numbers(hunk['context_code'])
                hunks_payload += f"\n=== NEW HUNK NUMBER {real_hunk_num} ===\nPROJECT: {hunk.get('project', 'Unknown')}\nCODE DIFF:\n{numbered_diff}\n"

            prompt = f"Evaluate these new code hunks sequentially using your Persona and historical patterns:\n{hunks_payload}"
            
            current_end = min(i + BATCH_SIZE, total_test_hunks)
            print(f"    -> Predicting Test Hunks {len(train_data) + i + 1} to {len(train_data) + current_end}... ", end="", flush=True)

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