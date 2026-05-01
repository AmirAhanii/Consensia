from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import SessionLocal
from .models import DebateRateBucket, User

logger = logging.getLogger(__name__)


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def effective_is_admin(user: User, settings: Settings) -> bool:
    if user.is_admin:
        return True
    return user.email.strip().lower() in settings.admin_emails


def anon_subject(request: Request, settings: Settings) -> str:
    xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    ip = xff or (request.client.host if request.client else "") or "unknown"
    salt = (settings.jwt_secret or "dev-quota-salt").encode()
    digest = hashlib.sha256(ip.encode() + b"|" + salt).hexdigest()
    return digest[:64]


def _get_bucket_count(db: Session, kind: str, subject: str, day: date) -> int:
    row = (
        db.query(DebateRateBucket)
        .filter(
            DebateRateBucket.kind == kind,
            DebateRateBucket.subject == subject,
            DebateRateBucket.day == day,
        )
        .first()
    )
    return row.count if row else 0


def assert_debate_quota_allowed(
    db: Session,
    settings: Settings,
    *,
    user: User | None,
    request: Request,
) -> tuple[str, str] | None:
    """Return (kind, subject) to increment after a successful debate, or None if unlimited (admin)."""
    today = utc_today()
    if user and effective_is_admin(user, settings):
        return None
    if user:
        kind, subject = "user", user.id
        limit = settings.user_daily_debate_limit
        current = _get_bucket_count(db, kind, subject, today)
        if current >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Daily debate limit reached ({limit} per day for signed-in accounts). "
                    "Try again tomorrow."
                ),
            )
        return (kind, subject)
    kind, subject = "anon", anon_subject(request, settings)
    limit = settings.anon_daily_debate_limit
    current = _get_bucket_count(db, kind, subject, today)
    if current >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily guest debate limit reached ({limit} per day). "
                "Sign in for a higher limit, or try again tomorrow."
            ),
        )
    return (kind, subject)


def record_successful_debate(db: Session, bucket: tuple[str, str] | None) -> None:
    if bucket is None:
        return
    kind, subject = bucket
    today = utc_today()
    row = (
        db.query(DebateRateBucket)
        .filter(
            DebateRateBucket.kind == kind,
            DebateRateBucket.subject == subject,
            DebateRateBucket.day == today,
        )
        .first()
    )
    if row:
        row.count += 1
    else:
        db.add(DebateRateBucket(kind=kind, subject=subject, day=today, count=1))


def sync_admin_flags_from_env() -> None:
    """Promote users whose email is listed in ADMIN_EMAILS to is_admin=true (idempotent)."""
    settings = get_settings()
    emails = list(settings.admin_emails)
    if not emails:
        return
    db = SessionLocal()
    try:
        db.execute(update(User).where(User.email.in_(emails)).values(is_admin=True))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to sync ADMIN_EMAILS to users.is_admin")
    finally:
        db.close()


def upgrade_user_if_listed_admin(user: User, settings: Settings) -> None:
    """Set is_admin when the account email appears in ADMIN_EMAILS (does not commit)."""
    if user.email.strip().lower() in settings.admin_emails:
        user.is_admin = True
