from app.services.scraping_service import scrape_google_scholar_author
from app.services.file_store import save_raw_author_json
from app.db.database import SessionLocal, engine, Base
from app.models.author import Author

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

    # 2. Save the JSON file first to get the path
    # We use a temporary string or the scholar_id for the filename 
    # since we don't have the DB 'id' yet.
    path = save_raw_author_json(scholar_id, raw) 

    # 3. Create the Author object with ALL required fields
    author = Author(
        name=raw["name"],
        scholar_id=scholar_id,
        affiliation=raw["affiliation"],
        raw_json_path=path  # <--- Now this is NOT NULL
        # Note: profile_url has been completely removed to match your new scraper
    )
    
    # 4. Save to Database in one go
    db.add(author)
    db.commit()
    db.refresh(author)

print("Scraping batch complete.")