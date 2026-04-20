from app.services.scraping_service import scrape_google_scholar_author
from app.services.file_store import save_raw_author_json
from app.db.database import SessionLocal, engine, Base
from app.models.author import Author

# Ensure tables exist
Base.metadata.create_all(bind=engine)

AUTHOR_IDS = [
    "Fac_e58AAAAJ",
    "WH-L4NoAAAAJ",
    "VlSBMuIAAAAJ"
]

db = SessionLocal()

for scholar_id in AUTHOR_IDS:
    # 1. Scrape the data
    raw = scrape_google_scholar_author(scholar_id)

    # 2. THE SAFETY GATE: If SerpApi failed or returned no name, SKIP it!
    if not raw or not raw.get("name"):
        print(f"[!] Warning: API Error or missing profile for '{scholar_id}'. Skipping database insert.")
        continue  # Safely jumps to the next author ID in the list

    # 3. Save the JSON file first to get the path
    # We use a temporary string or the scholar_id for the filename 
    # since we don't have the DB 'id' yet.
    path = save_raw_author_json(scholar_id, raw) 

    # 4. Create the Author object with ALL required fields
    author = Author(
        name=raw["name"],
        scholar_id=scholar_id,
        affiliation=raw.get("affiliation"), # Added .get() just in case affiliation is missing too
        raw_json_path=path  # <--- Now this is NOT NULL
        # Note: profile_url has been completely removed to match your new scraper
    )
    
    # 5. Save to Database in one go
    db.add(author)
    db.commit()
    db.refresh(author)

print("\n[SUCCESS] Scraping batch complete.")