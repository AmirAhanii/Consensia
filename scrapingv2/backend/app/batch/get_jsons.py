import json
import os
import time
from app.services.scraping_service import scrape_google_scholar_author

AUTHOR_IDS = [
    "Fac_e58AAAAJ",
    "WH-L4NoAAAAJ",
    "VlSBMuIAAAAJ"
]

def generate_jsons_only():
    # 1. Create a safe folder for the files
    output_dir = "raw_authors"
    os.makedirs(output_dir, exist_ok=True)

    for scholar_id in AUTHOR_IDS:
        print(f"\n========================================")
        print(f"--- Relentless Scraping: {scholar_id} ---")
        print(f"========================================")
        
        attempt = 1
        raw_data = None
        
        # 2. THE RETRY LOOP: Keep trying until we get a name AND papers
        while True:
            raw_data = scrape_google_scholar_author(scholar_id)
            
            # Check if we got a valid name AND at least 1 paper
            name = raw_data.get("name")
            papers = raw_data.get("papers", [])
            
            if name and len(papers) > 0:
                print(f"\n[SUCCESS] Attempt {attempt} worked! Found {len(papers)} papers for {name}.")
                break # Break out of the infinite loop, we got the data!
            else:
                print(f"\n[!] Attempt {attempt} failed (Returned 0 papers or no name).")
                print("Cooling down for 5 seconds before retrying...")
                time.sleep(5) # Pause to prevent getting banned
                attempt += 1

        # 3. Format the filename
        safe_name = raw_data["name"].replace(" ", "_").lower()
        filename = os.path.join(output_dir, f"raw_{safe_name}.json")
        
        # 4. Save the JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
        print(f"[FILE SAVED] Data safely written to: {filename}")

if __name__ == "__main__":
    generate_jsons_only()