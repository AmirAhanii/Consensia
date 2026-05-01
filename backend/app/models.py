from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    auth_identities = relationship("AuthIdentity", back_populates="user", cascade="all, delete-orphan")
    debate_sessions = relationship("DebateSession", back_populates="user", cascade="all, delete-orphan")
    email_verification_codes = relationship(
        "EmailVerificationCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    favorite_personas = relationship(
        "FavoritePersona",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AuthIdentity(Base):
    __tablename__ = "auth_identities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)  # local | google
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="auth_identities")


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="email_verification_codes")


class DebateSession(Base):
    __tablename__ = "debate_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="New Debate")
    question: Mapped[str] = mapped_column(Text, nullable=False, default="")
    personas: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="debate_sessions")
    messages = relationship(
        "DebateMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DebateMessage.created_at",
    )


class DebateMessage(Base):
    __tablename__ = "debate_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("debate_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # user | persona | judge | system
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    # Optional label for speaker (persona name, "You", "Judge")
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Optional: round metadata to group messages in UI
    round_number: Mapped[int | None] = mapped_column(nullable=True)
    round_label: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Optional persona metadata (for persona role)
    persona_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    persona_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    session = relationship("DebateSession", back_populates="messages")


class DebateRateBucket(Base):
    __tablename__ = "debate_rate_buckets"
    __table_args__ = (UniqueConstraint("kind", "subject", "day", name="uq_debate_rate_bucket_day"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FavoritePersona(Base):
    __tablename__ = "favorite_personas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="favorite_personas")