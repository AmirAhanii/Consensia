import os
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==========================================
# CONFIGURATION: THE FEW-SHOT SETUP
# ==========================================
RESEARCHERS = [
    {
        "name": "Alireza Aghamohammadi",
        "train_file": "aaghamohammadi_train.json",
        "test_file": "aaghamohammadi_test.json",
        "truth_key": "aaghamohammadi", 
        "output_file": "aaghamohammadi_fewshot_results.json"
    },
    {
        "name": "Alexander Trautsch",
        "train_file": "atrautsch_train.json",
        "test_file": "atrautsch_test.json",
        "truth_key": "atrautsch",
        "output_file": "atrautsch_fewshot_results.json"
    },
    {
        "name": "Steffen Herbold",
        "train_file": "sherbold_train.json",
        "test_file": "sherbold_test.json",
        "truth_key": "sherbold",
        "output_file": "sherbold_fewshot_results.json"
    }
]

# Cap the number of training examples so the prompt doesn't get too massive.
# 30 is a very strong number for Few-Shot learning. 
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
    reasoning: str = Field(description="Step-by-step logic identifying the patterns based on the examples.")
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
# THE FEW-SHOT PIPELINE
# ---------------------------------------------------------------------------
def run_pipeline():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "A"))
    BATCH_SIZE = 5

    for researcher in RESEARCHERS:
        print(f"\n==================================================")
        print(f" 🧠 STARTING FEW-SHOT FOR: {researcher['name']} 🧠 ")
        print(f"==================================================")

        # 1. Load Training and Testing Data
        try:
            with open(researcher['train_file'], 'r', encoding='utf-8') as f:
                train_data = json.load(f)
            with open(researcher['test_file'], 'r', encoding='utf-8') as f:
                test_data = json.load(f)
        except FileNotFoundError as e:
            print(f"[!] Missing file: {e}. Skipping.")
            continue

        # 2. Build the Few-Shot Examples String
        print(f"[*] Building Few-Shot examples from {researcher['train_file']}...")
        examples_string = ""
        example_count = min(len(train_data), MAX_FEW_SHOT_EXAMPLES)
        
        for i in range(example_count):
            hunk = train_data[i]
            numbered_diff = format_diff_with_line_numbers(hunk['context_code'])
            
            # Safely extract the ground truth labels
            truth_str = hunk.get(researcher['truth_key'], '{}')
            try:
                # We format it beautifully so the LLM easily understands the expected output
                truth_json = json.dumps(json.loads(truth_str), indent=2)
            except:
                truth_json = "{}"

            examples_string += f"\n--- EXAMPLE {i+1} ---\nCODE DIFF:\n{numbered_diff}\nCORRECT LABELS:\n{truth_json}\n"

        # 3. Create the System Instruction
        system_instruction = f"""
You are an expert scientific code annotator identifying "tangled commits".
Your task is to classify numbered lines of code diffs into categories.

You MUST follow the patterns, biases, and logic demonstrated in the examples below. 
Do not apply generic logic; strictly mimic the labeling style shown in these examples.

### TRAINING EXAMPLES:
{examples_string}

CRITICAL RULES:
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
                # We need to maintain the true hunk number for the metrics script
                # Since this is the test set, its real index is (split_index + i + idx + 1)
                real_hunk_num = len(train_data) + i + idx + 1
                
                numbered_diff = format_diff_with_line_numbers(hunk['context_code'])
                hunks_payload += f"\n=== NEW HUNK NUMBER {real_hunk_num} ===\nPROJECT: {hunk.get('project', 'Unknown')}\nCODE DIFF:\n{numbered_diff}\n"

            prompt = f"Using the patterns from your training examples, evaluate these new code hunks sequentially:\n{hunks_payload}"
            
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
                        temperature=0.1 # Very low temperature to force strict pattern matching
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