from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from ..auth.deps import require_admin
from ..config import Settings, get_settings
from ..db import get_db
from ..models import AuthIdentity, DebateMessage, DebateRateBucket, DebateSession, User
from .schemas import AdminStatsResponse, DailyPoint, QuotaSlice

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _quota_slice(
    *,
    rows: list[DebateRateBucket],
    limit_per_subject: int,
) -> QuotaSlice:
    debates = sum(r.count for r in rows)
    distinct = len(rows)
    if distinct <= 0:
        return QuotaSlice(
            debates=0,
            distinct_subjects=0,
            limit_per_subject=limit_per_subject,
            utilization_pct=0.0,
        )
    capacity = distinct * limit_per_subject
    pct = (debates / capacity) * 100.0 if capacity else 0.0
    return QuotaSlice(
        debates=debates,
        distinct_subjects=distinct,
        limit_per_subject=limit_per_subject,
        utilization_pct=min(100.0, round(pct, 2)),
    )


@router.get("/stats", response_model=AdminStatsResponse)
def admin_stats(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminStatsResponse:
    now = datetime.now(timezone.utc)
    today = _utc_today()
    start_14 = today - timedelta(days=13)
    start_7 = now - timedelta(days=7)
    start_30 = now - timedelta(days=30)

    users_total = int(db.scalar(select(func.count()).select_from(User)) or 0)
    users_verified = int(
        db.scalar(select(func.count()).select_from(User).where(User.is_email_verified.is_(True))) or 0
    )
    users_unverified = max(0, users_total - users_verified)

    users_with_google = int(
        db.scalar(
            select(func.count(func.distinct(AuthIdentity.user_id))).where(AuthIdentity.provider == "google")
        )
        or 0
    )
    users_with_local = int(
        db.scalar(
            select(func.count(func.distinct(AuthIdentity.user_id))).where(AuthIdentity.provider == "local")
        )
        or 0
    )

    sessions_total = int(db.scalar(select(func.count()).select_from(DebateSession)) or 0)
    sessions_last_7_days = int(
        db.scalar(select(func.count()).select_from(DebateSession).where(DebateSession.created_at >= start_7))
        or 0
    )
    sessions_last_30_days = int(
        db.scalar(select(func.count()).select_from(DebateSession).where(DebateSession.created_at >= start_30))
        or 0
    )

    messages_total = int(db.scalar(select(func.count()).select_from(DebateMessage)) or 0)

    anon_today = (
        db.query(DebateRateBucket)
        .filter(DebateRateBucket.kind == "anon", DebateRateBucket.day == today)
        .all()
    )
    user_today = (
        db.query(DebateRateBucket)
        .filter(DebateRateBucket.kind == "user", DebateRateBucket.day == today)
        .all()
    )

    debates_today_total = sum(r.count for r in anon_today) + sum(r.count for r in user_today)

    debates_last_14 = (
        db.execute(
            select(func.coalesce(func.sum(DebateRateBucket.count), 0)).where(DebateRateBucket.day >= start_14)
        ).scalar_one()
    )
    debates_last_14_days_total = int(debates_last_14 or 0)

    kind_rows = (
        db.execute(
            select(DebateRateBucket.kind, func.coalesce(func.sum(DebateRateBucket.count), 0))
            .where(DebateRateBucket.day >= start_14)
            .group_by(DebateRateBucket.kind)
        )
        .all()
    )
    debate_volume_by_kind_14d = {str(k): int(v or 0) for k, v in kind_rows}

    signup_rows = (
        db.execute(
            select(cast(User.created_at, Date).label("d"), func.count(User.id))
            .where(cast(User.created_at, Date) >= start_14)
            .group_by(cast(User.created_at, Date))
        )
        .all()
    )
    signup_map: dict[date, int] = {r[0]: int(r[1]) for r in signup_rows if r[0] is not None}

    debate_day_rows = (
        db.execute(
            select(DebateRateBucket.day, func.coalesce(func.sum(DebateRateBucket.count), 0)).where(
                DebateRateBucket.day >= start_14
            ).group_by(DebateRateBucket.day)
        )
        .all()
    )
    debate_day_map: dict[date, int] = {r[0]: int(r[1]) for r in debate_day_rows if r[0] is not None}

    sess_day_rows = (
        db.execute(
            select(cast(DebateSession.created_at, Date).label("d"), func.count(DebateSession.id))
            .where(cast(DebateSession.created_at, Date) >= start_14)
            .group_by(cast(DebateSession.created_at, Date))
        )
        .all()
    )
    sess_day_map: dict[date, int] = {r[0]: int(r[1]) for r in sess_day_rows if r[0] is not None}

    series: list[DailyPoint] = []
    d = start_14
    while d <= today:
        series.append(
            DailyPoint(
                day=d,
                signups=signup_map.get(d, 0),
                debates_recorded=debate_day_map.get(d, 0),
                sessions_created=sess_day_map.get(d, 0),
            )
        )
        d += timedelta(days=1)

    return AdminStatsResponse(
        generated_at=now.isoformat(),
        users_total=users_total,
        users_verified=users_verified,
        users_unverified=users_unverified,
        users_with_google=users_with_google,
        users_with_local=users_with_local,
        sessions_total=sessions_total,
        sessions_last_7_days=sessions_last_7_days,
        sessions_last_30_days=sessions_last_30_days,
        messages_total=messages_total,
        debates_today_total=debates_today_total,
        debates_last_14_days_total=debates_last_14_days_total,
        quotas_today={
            "anon": _quota_slice(rows=anon_today, limit_per_subject=settings.anon_daily_debate_limit),
            "user": _quota_slice(rows=user_today, limit_per_subject=settings.user_daily_debate_limit),
        },
        limits={
            "user_daily_debate_limit": settings.user_daily_debate_limit,
            "anon_daily_debate_limit": settings.anon_daily_debate_limit,
        },
        debate_volume_by_kind_14d=debate_volume_by_kind_14d,
        series_last_14_days=series,
    )
