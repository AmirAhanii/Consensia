from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user_id
from ..db import get_db
from ..models import FavoritePersona

router = APIRouter(prefix="/api/persona-favorites", tags=["persona-favorites"])


class FavoritePersonaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=8000)
    icon: str = Field(..., min_length=1, max_length=64)


class FavoritePersonaOut(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    created_at: str


def _serialize(row: FavoritePersona) -> FavoritePersonaOut:
    return FavoritePersonaOut(
        id=row.id,
        name=row.name,
        description=row.description,
        icon=row.icon,
        created_at=row.created_at.isoformat(),
    )


@router.get("", response_model=list[FavoritePersonaOut])
async def list_favorites(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(FavoritePersona)
        .filter(FavoritePersona.user_id == user_id)
        .order_by(FavoritePersona.created_at.desc())
        .all()
    )
    return [_serialize(r) for r in rows]


@router.post("", response_model=FavoritePersonaOut)
async def add_favorite(
    payload: FavoritePersonaCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    description = payload.description.strip()
    icon = payload.icon.strip()
    if not name or not description or not icon:
        raise HTTPException(status_code=400, detail="Name, description, and icon are required.")

    existing = (
        db.query(FavoritePersona)
        .filter(
            FavoritePersona.user_id == user_id,
            FavoritePersona.name == name,
            FavoritePersona.description == description,
            FavoritePersona.icon == icon,
        )
        .first()
    )
    if existing:
        return _serialize(existing)

    row = FavoritePersona(
        user_id=user_id,
        name=name,
        description=description,
        icon=icon,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/{favorite_id}")
async def remove_favorite(
    favorite_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    row = (
        db.query(FavoritePersona)
        .filter(FavoritePersona.id == favorite_id, FavoritePersona.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
