import json
import os
import time

# Pointing to your new pipeline
from app.services.persona_pipeline import generate_persona_from_raw

# Define where the raw files are and where the final personas should go
INPUT_DIR = "data/raw_authors"
OUTPUT_DIR = "data/personas"

def run_standalone_pipeline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(INPUT_DIR):
        print(f"[!] Error: Could not find folder '{INPUT_DIR}'.")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    print(f"Found {len(files)} files to process in {INPUT_DIR}...\n")

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        print(f"========================================")
        print(f"--- Processing: {filename} ---")
        print(f"========================================")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            author_name = raw_data.get("name", "Unknown Author")
            
            print(f"Triggering LLM pipeline for {author_name}...")
            
            persona = generate_persona_from_raw(
                raw_author=raw_data,
                author_name=author_name,
                raw_filename=filepath
            )

            safe_name = author_name.replace(" ", "_").lower()
            output_path = os.path.join(OUTPUT_DIR, f"persona_{safe_name}_v1.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                if isinstance(persona, str):
                    f.write(persona)
                else:
                    json.dump(persona, f, indent=2, ensure_ascii=False)
                    
            print(f"[SUCCESS] Persona safely written to {output_path}")

            print("Waiting 20 seconds to respect API limits before the next author...")
            time.sleep(20)

        except Exception as e:
            print(f"\n[ERROR] Failed to process {filename}: {e}")
            if "429" in str(e):
                print("Quota hit! Sleeping for 60 seconds to cool down...")
                time.sleep(60)

if __name__ == "__main__":
    run_standalone_pipeline()