from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class QuotaSlice(BaseModel):
    debates: int = 0
    distinct_subjects: int = 0
    limit_per_subject: int
    utilization_pct: float = Field(
        ...,
        description="Rough share of per-subject daily capacity used (0–100, capped).",
    )


class DailyPoint(BaseModel):
    day: date
    signups: int = 0
    debates_recorded: int = 0
    sessions_created: int = 0


class AdminStatsResponse(BaseModel):
    generated_at: str

    users_total: int
    users_verified: int
    users_unverified: int
    users_with_google: int
    users_with_local: int

    sessions_total: int
    sessions_last_7_days: int
    sessions_last_30_days: int

    messages_total: int

    debates_today_total: int
    debates_last_14_days_total: int

    quotas_today: dict[str, QuotaSlice]
    limits: dict[str, int]

    debate_volume_by_kind_14d: dict[str, int]

    series_last_14_days: list[DailyPoint]


class AdminUserRow(BaseModel):
    id: str
    email: str
    full_name: str
    is_email_verified: bool
    is_admin: bool
    created_at: datetime
    auth_providers: list[str]


class AdminUsersListResponse(BaseModel):
    users: list[AdminUserRow]


class AdminUserAdminPatch(BaseModel):
    is_admin: bool = Field(..., description="Grant or revoke workspace admin (unlimited debates + admin UI).")
