from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import User, AuthIdentity, EmailVerificationCode, PasswordResetCode


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = (
        select(User)
        .where(User.email == email.strip().lower())
        .options(
            selectinload(User.auth_identities),
            selectinload(User.email_verification_codes),
        )
    )
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_id: str) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.auth_identities),
            selectinload(User.email_verification_codes),
        )
    )
    return db.scalar(stmt)


def get_user_by_google_sub(db: Session, google_sub: str) -> User | None:
    stmt = (
        select(User)
        .join(AuthIdentity)
        .where(
            AuthIdentity.provider == "google",
            AuthIdentity.google_sub == google_sub,
        )
        .options(selectinload(User.auth_identities))
    )
    return db.scalar(stmt)


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    is_email_verified: bool = False,
) -> User:
    user = User(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        is_email_verified=is_email_verified,
    )
    db.add(user)
    db.flush()
    return user


def create_local_identity(
    db: Session,
    *,
    user_id: str,
    password_hash: str,
) -> AuthIdentity:
    identity = AuthIdentity(
        user_id=user_id,
        provider="local",
        password_hash=password_hash,
    )
    db.add(identity)
    db.flush()
    return identity


def create_google_identity(
    db: Session,
    *,
    user_id: str,
    google_sub: str,
) -> AuthIdentity:
    identity = AuthIdentity(
        user_id=user_id,
        provider="google",
        google_sub=google_sub,
    )
    db.add(identity)
    db.flush()
    return identity


def get_local_identity(db: Session, user_id: str) -> AuthIdentity | None:
    stmt = select(AuthIdentity).where(
        AuthIdentity.user_id == user_id,
        AuthIdentity.provider == "local",
    )
    return db.scalar(stmt)


def get_google_identity(db: Session, google_sub: str) -> AuthIdentity | None:
    stmt = select(AuthIdentity).where(
        AuthIdentity.provider == "google",
        AuthIdentity.google_sub == google_sub,
    )
    return db.scalar(stmt)


def create_email_verification_code(
    db: Session,
    *,
    user_id: str,
    code_hash: str,
    expires_at: datetime,
) -> EmailVerificationCode:
    code = EmailVerificationCode(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=expires_at,
    )
    db.add(code)
    db.flush()
    return code


def get_active_verification_code(
    db: Session,
    *,
    code_hash: str,
) -> EmailVerificationCode | None:
    stmt = (
        select(EmailVerificationCode)
        .where(EmailVerificationCode.code_hash == code_hash)
        .options(selectinload(EmailVerificationCode.user))
    )
    code = db.scalar(stmt)
    if not code:
        return None
    if code.used_at is not None:
        return None
    if code.expires_at <= datetime.utcnow().astimezone():
        return None
    return code


def mark_email_verified(
    db: Session,
    *,
    user: User,
    code: EmailVerificationCode,
    verified_at: datetime,
) -> None:
    user.is_email_verified = True
    user.updated_at = verified_at
    code.used_at = verified_at
    db.add(user)
    db.add(code)
    db.flush()


def invalidate_unused_verification_codes(
    db: Session,
    *,
    user_id: str,
    invalidated_at: datetime,
) -> None:
    stmt = select(EmailVerificationCode).where(
        EmailVerificationCode.user_id == user_id
    )
    codes = db.scalars(stmt).all()

    for code in codes:
        if code.used_at is None:
            code.used_at = invalidated_at
            db.add(code)

    db.flush()


def create_password_reset_code(
    db: Session,
    *,
    user_id: str,
    code_hash: str,
    expires_at: datetime,
) -> PasswordResetCode:
    row = PasswordResetCode(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=expires_at,
    )
    db.add(row)
    db.flush()
    return row


def get_active_password_reset_code(
    db: Session,
    *,
    code_hash: str,
) -> PasswordResetCode | None:
    stmt = select(PasswordResetCode).where(PasswordResetCode.code_hash == code_hash)
    code = db.scalar(stmt)
    if not code:
        return None
    if code.used_at is not None:
        return None
    if code.expires_at <= datetime.now(timezone.utc):
        return None
    return code


def invalidate_unused_password_reset_codes(
    db: Session,
    *,
    user_id: str,
    invalidated_at: datetime,
) -> None:
    stmt = select(PasswordResetCode).where(PasswordResetCode.user_id == user_id)
    codes = db.scalars(stmt).all()
    for code in codes:
        if code.used_at is None:
            code.used_at = invalidated_at
            db.add(code)
    db.flush()


def mark_password_reset_code_used(
    db: Session,
    *,
    code: PasswordResetCode,
    used_at: datetime,
) -> None:
    code.used_at = used_at
    db.add(code)
    db.flush()