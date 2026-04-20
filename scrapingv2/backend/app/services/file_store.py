import json
from pathlib import Path
from app.core.config import settings

# Initialize directories from config
DATA_DIR = Path(settings.data_dir)
RAW_DIR = DATA_DIR / "raw_authors"
PERSONA_DIR = DATA_DIR / "personas"

# Ensure base directories exist immediately 
RAW_DIR.mkdir(parents=True, exist_ok=True)
PERSONA_DIR.mkdir(parents=True, exist_ok=True)

def save_raw_author_json(identifier: str, data: dict) -> str:
    """Saves raw data using scholar_id or DB id as filename."""
    path = RAW_DIR / f"{identifier}_raw.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(path)

def load_raw_author_json(identifier: str) -> dict:
    """Loads raw data based on the provided identifier."""
    path = RAW_DIR / f"{identifier}_raw.json"
    if not path.exists():
        # Helpful error for debugging Stage 1 vs Stage 2 mismatches
        raise FileNotFoundError(f"Missing raw data at {path}. Run scraping first.")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_persona_json(author_id: int, version: str, data: dict) -> str:
    """Saves versioned persona JSON."""
    subdir = PERSONA_DIR / version
    subdir.mkdir(parents=True, exist_ok=True)
    path = subdir / f"{author_id}_persona_{version}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(path)

def load_persona_json_by_path(path_str: str) -> dict:
    """Loads persona for experiment execution[cite: 3]."""
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)