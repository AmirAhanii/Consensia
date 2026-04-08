import os
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 1. SCHEMA DEFINITIONS (Unchanged)
# ---------------------------------------------------------------------------
class LabelCategories(BaseModel):
    bugfix: list[int] = Field(description="Line indices that are part of the bugfix. [] if none.")
    whitespace: list[int] = Field(description="Line indices that are whitespace. [] if none.")
    documentation: list[int] = Field(description="Line indices that are documentation. [] if none.")
    refactoring: list[int] = Field(description="Line indices that are refactoring. [] if none.")
    test: list[int] = Field(description="Line indices that are tests. [] if none.")
    unrelated: list[int] = Field(description="Line indices that are unrelated. [] if none.")

class HunkAnnotation(BaseModel):
    hunk_number: int = Field(description="The index of the hunk being evaluated (1, 2, 3...)")
    persona_lens: str = Field(description="A brief statement in the persona's voice explaining their priority.")
    reasoning: str = Field(description="Step-by-step logic determining the labels, referencing line numbers.")
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
# 2. THE CHUNKING PIPELINE
# ---------------------------------------------------------------------------
def run_pipeline():
    # REMEMBER: Add your API key here if you aren't using the environment variable!
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "A"))

    with open('stage4-alireza.json', 'r', encoding='utf-8') as f:
        persona_data = json.load(f)
        
    with open('aaghamohammadi_only_context.json', 'r', encoding='utf-8') as f:
        all_hunks = json.load(f)

    total_hunks = len(all_hunks)
    BATCH_SIZE = 5 # Process 5 hunks at a time
    all_results = []

    print(f"\n[START] Found {total_hunks} hunks. Processing in batches of {BATCH_SIZE}...")
    print("-" * 50)

    # Loop through the data in chunks of 5
    for i in range(0, total_hunks, BATCH_SIZE):
        batch_hunks = all_hunks[i : i + BATCH_SIZE]
        
        # Build the payload just for this specific chunk
        hunks_payload = ""
        for idx, hunk in enumerate(batch_hunks, start=i+1):
            numbered_diff = format_diff_with_line_numbers(hunk['context_code'])
            hunks_payload += f"\n=== HUNK NUMBER {idx} ===\nPROJECT: {hunk.get('project', 'Unknown')}\nCODE DIFF:\n{numbered_diff}\n"

        system_instruction = f"""
You are participating in a scientific code annotation task to identify "tangled commits".
Adopt the following persona completely based on this JSON definition:
{json.dumps(persona_data, indent=2)}

THE TASK:
I will provide you with several code hunks. I have pre-numbered the changed lines (e.g., 'Line 0:', 'Line 1:').
Classify every numbered line into the provided JSON categories.

CRITICAL RULES:
- Isolate the true bugfix from unrelated noise or refactorings based strictly on your persona's biases.
- If a category does not apply to any lines, you MUST output an empty array [] for that category.
"""
        prompt = f"Evaluate the following code hunks sequentially using your assigned Persona.\n{hunks_payload}"

        current_end = min(i + BATCH_SIZE, total_hunks)
        print(f"[*] Sending Hunks {i+1} to {current_end} to Gemini API... ", end="", flush=True)

        try:
            # 1. Make the API Call
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=BatchAnnotationResult,
                    temperature=0.2 
                ),
            )

            # 2. Parse the text back into a Python Dictionary
            batch_result_dict = json.loads(response.text)
            
            # 3. Add the new results to our master list
            all_results.extend(batch_result_dict.get("results", []))
            
            # 4. AUTO-SAVE: Write everything processed so far to the hard drive
            with open('aaghamohammadi_api_results.json', 'w', encoding='utf-8') as f:
                json.dump({"results": all_results}, f, indent=2)
                
            print("Done! (Auto-saved)")

            # Small pause to avoid hitting the API too hard
            time.sleep(1)

        except Exception as e:
            print(f"\n[!] ERROR on Hunks {i+1}-{current_end}: {e}")
            print("[!] Skipping this batch and moving to the next one to keep the pipeline alive...")
            time.sleep(5) # Cooldown before trying the next batch

    print("-" * 50)
    print(f"[SUCCESS] All batches completed! Final data saved to 'aaghamohammadi_api_results.json'")

if __name__ == "__main__":
    run_pipeline()