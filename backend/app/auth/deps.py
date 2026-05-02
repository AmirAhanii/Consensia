from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..debate_quota import effective_is_admin
from ..models import User
from .repository import get_user_by_id
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
    try:
        return decode_access_token(credentials.credentials, settings.jwt_secret)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str | None:
    if not credentials:
        return None
    if not settings.jwt_secret:
        return None
    try:
        return decode_access_token(credentials.credentials, settings.jwt_secret)
    except Exception:
        return None


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    if not effective_is_admin(user, settings):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
