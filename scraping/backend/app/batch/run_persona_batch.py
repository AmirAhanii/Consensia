import time #
from app.db.database import SessionLocal, engine, Base
from app.models.author import Author
from app.models.persona import Persona
from app.services.persona_pipeline import generate_persona_from_raw
from app.services.file_store import load_raw_author_json, save_persona_json

# Ensure all tables (authors, personas, experiments) are ready [cite: 4, 5]
Base.metadata.create_all(bind=engine)

db = SessionLocal()
authors = db.query(Author).all()

print(f"Starting persona generation for {len(authors)} authors...")

for author in authors:
    try:
        print(f"--- Processing: {author.name} ---")
        
        # Load raw data using the scholar_id as we fixed earlier
        raw = load_raw_author_json(author.scholar_id)
        
        # This triggers the 4-stage LLM pipeline 
        persona = generate_persona_from_raw(
            raw_author=raw,
            author_name=author.name,
            raw_filename=author.raw_json_path,
        )

        # Versioned storage as per Section 4 of Research Log [cite: 4]
        path = save_persona_json(author.id, "v1", persona)

        db.add(Persona(
            author_id=author.id,
            name=f"{author.name}_v1",
            version="v1",
            model_name="gemini-2.0-flash", # Aligned with Log Section 7 
            persona_json_path=path
        ))
        db.commit()
        print(f"Successfully saved persona for {author.name} to {path}")

        # RATE LIMITING: The Free Tier requires cooling off periods.
        # 15-20 seconds is usually safe for the minute-based quota.
        print("Waiting 20 seconds to respect API rate limits...")
        time.sleep(20) 

    except Exception as e:
        print(f"Error processing {author.name}: {e}")
        db.rollback() # Prevent hanging transactions on failure
        # If we hit a 429 specifically, wait even longer
        if "429" in str(e):
            print("Quota hit. Sleeping for 60 seconds before retry...")
            time.sleep(60)
        continue

print("Persona batch complete.")