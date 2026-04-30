from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from ..auth.deps import get_current_user_id
from ..db import get_db
from ..models import DebateSession

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: str
    question: str = ""
    personas: list[dict] = []
    result: dict | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    question: str | None = None
    personas: list[dict] | None = None
    result: dict | None = None


def _out(s: DebateSession) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "question": s.question,
        "personas": json.loads(s.personas or "[]"),
        "result": json.loads(s.result) if s.result else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


@router.get("")
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    sessions = (
        db.query(DebateSession)
        .filter(DebateSession.user_id == user_id)
        .order_by(DebateSession.updated_at.desc())
        .all()
    )
    return [_out(s) for s in sessions]


@router.post("")
async def create_session(
    payload: SessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    session = DebateSession(
        user_id=user_id,
        title=payload.title or "New Debate",
        question=payload.question,
        personas=json.dumps(payload.personas),
        result=json.dumps(payload.result) if payload.result is not None else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _out(session)


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    payload: SessionUpdate,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    session = (
        db.query(DebateSession)
        .filter(DebateSession.id == session_id, DebateSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.title is not None:
        session.title = payload.title
    if payload.question is not None:
        session.question = payload.question
    if payload.personas is not None:
        session.personas = json.dumps(payload.personas)
    if payload.result is not None:
        session.result = json.dumps(payload.result)

    from datetime import timezone
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return _out(session)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    session = (
        db.query(DebateSession)
        .filter(DebateSession.id == session_id, DebateSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}
