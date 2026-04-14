from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
import json

from app.db.database import Base, engine, get_db
from app.models.author import Author
from app.models.persona import Persona
from app.schemas.author import AuthorCreate, Author as AuthorSchema
from app.schemas.persona import Persona as PersonaSchema, AskPersonaRequest
from app.services.file_store import save_raw_author_json, save_persona_json, load_persona_json_by_path
from app.services.persona_pipeline import generate_persona_from_raw
from app.core.llm_client import LLMClient

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SE Persona Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.post("/authors/from-raw-json", response_model=AuthorSchema)
async def create_author_from_raw_json(
    author: AuthorCreate,
    raw_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    For first tests:
    - You manually prepare a raw_author.json file (matching our schema).
    - Upload it here along with basic author info.
    - We save it and create an Author row.
    """
    contents = await raw_file.read()
    try:
        raw_data = json.loads(contents.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    # Create author row
    db_author = Author(
        name=author.name,
        scholar_id=author.scholar_id,
        affiliation=author.affiliation,
        profile_url=author.profile_url,
    )
    db.add(db_author)
    db.commit()
    db.refresh(db_author)

    # Save raw JSON file using generated author_id
    raw_path = save_raw_author_json(db_author.id, raw_data)
    db_author.raw_json_path = raw_path
    db.commit()
    db.refresh(db_author)

    return db_author


@app.post("/authors/{author_id}/generate-persona", response_model=PersonaSchema)
def generate_persona_endpoint(author_id: int, db: Session = Depends(get_db)):
    author = db.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    if not author.raw_json_path:
        raise HTTPException(status_code=400, detail="Author has no raw JSON path")

    # Load raw JSON
    raw_path = Path(author.raw_json_path)
    with raw_path.open("r", encoding="utf-8") as f:
        raw_author = json.load(f)

    persona_dict = generate_persona_from_raw(
        raw_author=raw_author,
        author_name=author.name,
        raw_filename=raw_path.name,
    )

    persona_path = save_persona_json(author.id, "v1", persona_dict)

    db_persona = Persona(
        author_id=author.id,
        name=f"{author.name}_v1",
        version="v1",
        model_name="gemini",
        persona_json_path=persona_path,
    )
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona


@app.get("/personas/{persona_id}", response_model=PersonaSchema)
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@app.post("/personas/{persona_id}/ask")
def ask_persona(
    persona_id: int,
    body: AskPersonaRequest,
    db: Session = Depends(get_db),
):
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    persona_json = load_persona_json_by_path(persona.persona_json_path)

    # Build a system prompt that injects persona behavior
    system_prompt = (
        "You are simulating the following Software Engineering research persona.\n\n"
        f"Persona JSON:\n{json.dumps(persona_json, ensure_ascii=False, indent=2)}\n\n"
        "When answering, you MUST stay consistent with this persona's expertise, "
        "methodological preferences, evaluation style, and communication style. "
        "Respond as this persona would respond."
    )

    user_prompt = f"Question: {body.question}"

    llm = LLMClient()
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    resp = llm.model.generate_content(full_prompt)
    answer = resp.text.strip()

    return {"persona_id": persona_id, "answer": answer}
