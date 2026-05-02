from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models import AuthIdentity, PasswordResetCode, User
from ..debate_quota import effective_is_admin, upgrade_user_if_listed_admin
from ..db import get_db
from .deps import get_current_user_id
from .emailer import send_password_reset_email_if_configured, send_verification_email_if_configured
from .google_auth import verify_google_credential
from .repository import (
    create_email_verification_code,
    create_google_identity,
    create_local_identity,
    create_password_reset_code,
    create_user,
    get_active_password_reset_code,
    get_active_verification_code,
    get_local_identity,
    get_user_by_email,
    get_user_by_google_sub,
    get_user_by_id,
    invalidate_unused_password_reset_codes,
    invalidate_unused_verification_codes,
    mark_email_verified,
    mark_password_reset_code_used,
)
from .schemas import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    VerifyEmailCodeRequest,
    VerifyPasswordResetCodeRequest,
)
from .security import (
    create_access_token,
    hash_password,
    hash_verification_code,
    new_email_verification_code,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _bg_send_verification_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    mail_from: str,
    to_email: str,
    raw_code: str,
) -> None:
    """Runs after HTTP response so the client is not blocked on SMTP (slow on Render cold paths)."""
    send_verification_email_if_configured(
        smtp_host,
        smtp_port,
        smtp_user,
        smtp_password,
        mail_from,
        to_email,
        raw_code,
    )


def _bg_send_password_reset_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    mail_from: str,
    to_email: str,
    raw_code: str,
) -> None:
    send_password_reset_email_if_configured(
        smtp_host,
        smtp_port,
        smtp_user,
        smtp_password,
        mail_from,
        to_email,
        raw_code,
    )


def _user_has_google_identity(db: Session, user_id: str) -> bool:
    row = db.execute(
        select(AuthIdentity.id).where(
            AuthIdentity.user_id == user_id,
            AuthIdentity.provider == "google",
        ).limit(1)
    ).scalar_one_or_none()
    return row is not None


def _primary_auth_provider(user) -> str:
    identities = list(user.auth_identities or [])
    if any(i.provider == "local" and i.password_hash for i in identities):
        return "local"
    if any(i.provider == "google" for i in identities):
        return "google"
    return "unknown"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/register")
async def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    existing = get_user_by_email(db, payload.email)

    if existing:
        if existing.is_email_verified:
            raise HTTPException(status_code=400, detail="Email already registered")

        raw_code, code_hash = new_email_verification_code()
        expires_at = utcnow() + timedelta(hours=24)

        invalidate_unused_verification_codes(
            db,
            user_id=existing.id,
            invalidated_at=utcnow(),
        )

        create_email_verification_code(
            db,
            user_id=existing.id,
            code_hash=code_hash,
            expires_at=expires_at,
        )

        db.commit()

        background_tasks.add_task(
            _bg_send_verification_email,
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_user,
            settings.smtp_password,
            settings.mail_from,
            existing.email,
            raw_code,
        )
        return {
            "message": (
                "Account already exists but is not verified. A verification email is being sent—"
                "check your inbox (and spam) shortly. If nothing arrives, check the API server logs for the code."
            )
        }

    password_hash = hash_password(payload.password)
    raw_code, code_hash = new_email_verification_code()
    expires_at = utcnow() + timedelta(hours=24)

    user = create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        is_email_verified=False,
    )
    upgrade_user_if_listed_admin(user, settings)

    create_local_identity(
        db,
        user_id=user.id,
        password_hash=password_hash,
    )

    create_email_verification_code(
        db,
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    db.commit()

    background_tasks.add_task(
        _bg_send_verification_email,
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        settings.mail_from,
        user.email,
        raw_code,
    )
    return {
        "message": (
            "Registration successful. A verification email is being sent—check your inbox (and spam) shortly. "
            "If it does not arrive, check the API server logs for the verification code, then continue to the verify page."
        )
    }


@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailCodeRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    code_hash = hash_verification_code(payload.code)
    verification_code = get_active_verification_code(db, code_hash=code_hash)

    if not verification_code:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    if verification_code.user_id != user.id:
        raise HTTPException(status_code=400, detail="Verification code does not match this email")

    mark_email_verified(
        db,
        user=user,
        code=verification_code,
        verified_at=utcnow(),
    )

    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = get_user_by_email(db, payload.email)

    if not user:
        return {"message": "If an account with that email exists, a verification code has been sent."}

    if user.is_email_verified:
        return {"message": "This email is already verified. Please log in."}

    raw_code, code_hash = new_email_verification_code()
    expires_at = utcnow() + timedelta(hours=24)

    invalidate_unused_verification_codes(
        db,
        user_id=user.id,
        invalidated_at=utcnow(),
    )

    create_email_verification_code(
        db,
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    db.commit()

    background_tasks.add_task(
        _bg_send_verification_email,
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        settings.mail_from,
        user.email,
        raw_code,
    )
    return {
        "message": (
            "A new verification email is being sent—check your inbox shortly. "
            "If it does not arrive, check the API server logs for the verification code."
        )
    }


_FORGOT_PASSWORD_GENERIC_MESSAGE = (
    "If an account with that email exists and supports password reset, "
    "we sent a 6-digit code to that address."
)


def _active_password_reset_for_code(
    db: Session,
    *,
    email: str,
    code: str,
) -> tuple[User, AuthIdentity, PasswordResetCode] | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    local_identity = get_local_identity(db, user.id)
    if not local_identity or not local_identity.password_hash:
        return None
    code_hash = hash_verification_code(code)
    reset_row = get_active_password_reset_code(db, code_hash=code_hash)
    if not reset_row or reset_row.user_id != user.id:
        return None
    return user, local_identity, reset_row


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = get_user_by_email(db, payload.email)
    if not user:
        return {"message": _FORGOT_PASSWORD_GENERIC_MESSAGE}

    local_identity = get_local_identity(db, user.id)
    if not local_identity or not local_identity.password_hash:
        return {"message": _FORGOT_PASSWORD_GENERIC_MESSAGE}

    raw_code, code_hash = new_email_verification_code()
    expires_at = utcnow() + timedelta(hours=24)

    invalidate_unused_password_reset_codes(
        db,
        user_id=user.id,
        invalidated_at=utcnow(),
    )

    create_password_reset_code(
        db,
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    db.commit()

    background_tasks.add_task(
        _bg_send_password_reset_email,
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        settings.mail_from,
        user.email,
        raw_code,
    )

    return {"message": _FORGOT_PASSWORD_GENERIC_MESSAGE}


@router.post("/verify-password-reset-code")
async def verify_password_reset_code(
    payload: VerifyPasswordResetCodeRequest,
    db: Session = Depends(get_db),
):
    resolved = _active_password_reset_for_code(
        db,
        email=str(payload.email),
        code=payload.code,
    )
    if not resolved:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code",
        )
    return {"message": "Code verified"}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    resolved = _active_password_reset_for_code(
        db,
        email=str(payload.email),
        code=payload.code,
    )
    if not resolved:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code",
        )
    user, local_identity, reset_row = resolved

    now = utcnow()
    local_identity.password_hash = hash_password(payload.new_password)
    user.updated_at = now
    mark_password_reset_code_used(db, code=reset_row, used_at=now)
    db.add(local_identity)
    db.add(user)
    db.commit()

    return {"message": "Password reset successful. You can log in with your new password."}


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="No account exists for this email address.",
        )

    local_identity = get_local_identity(db, user.id)
    if not local_identity or not local_identity.password_hash:
        if _user_has_google_identity(db, user.id):
            raise HTTPException(
                status_code=401,
                detail='This account uses Google sign-in. Use "Continue with Google" instead of a password.',
            )
        raise HTTPException(
            status_code=401,
            detail="No password is set for this account. Try “Forgot password” or register again.",
        )

    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")

    if not verify_password(payload.password, local_identity.password_hash):
        raise HTTPException(
            status_code=401,
            detail="The password does not match this email address.",
        )

    upgrade_user_if_listed_admin(user, settings)
    if user.email.strip().lower() in settings.admin_emails:
        db.add(user)
        db.commit()

    token = create_access_token(
        str(user.id),
        settings.jwt_secret,
        settings.access_token_expire_minutes,
    )
    return TokenResponse(access_token=token)


@router.post("/google", response_model=TokenResponse)
async def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is not configured")

    info = verify_google_credential(payload.credential, settings.google_client_id)

    google_sub = info["sub"]
    email = info.get("email")
    full_name = info.get("name") or "Google User"
    email_verified = bool(info.get("email_verified"))

    user = get_user_by_google_sub(db, google_sub)

    if not user and email:
        user = get_user_by_email(db, email)
        if user:
            create_google_identity(
                db,
                user_id=user.id,
                google_sub=google_sub,
            )

    if not user:
        if not email:
            raise HTTPException(status_code=400, detail="Google account did not provide an email")

        user = create_user(
            db,
            full_name=full_name,
            email=email,
            is_email_verified=email_verified,
        )
        create_google_identity(
            db,
            user_id=user.id,
            google_sub=google_sub,
        )

    upgrade_user_if_listed_admin(user, settings)
    db.commit()

    token = create_access_token(
        str(user.id),
        settings.jwt_secret,
        settings.access_token_expire_minutes,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def read_profile(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_email_verified=user.is_email_verified,
        auth_provider=_primary_auth_provider(user),
        is_admin=effective_is_admin(user, settings),
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.full_name = payload.full_name.strip()
    user.updated_at = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_email_verified=user.is_email_verified,
        auth_provider=_primary_auth_provider(user),
        is_admin=effective_is_admin(user, settings),
    )


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    local_identity = get_local_identity(db, user.id)
    if not local_identity or not local_identity.password_hash:
        raise HTTPException(
            status_code=400,
            detail="Password change is only available for email/password sign-in.",
        )
    if not verify_password(payload.current_password, local_identity.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    local_identity.password_hash = hash_password(payload.new_password)
    db.add(local_identity)
    db.commit()
    return {"message": "Password updated"}


@router.post("/delete-account")
async def delete_account(
    payload: DeleteAccountRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    local_identity = get_local_identity(db, user.id)
    if not local_identity or not local_identity.password_hash:
        raise HTTPException(
            status_code=400,
            detail="Account deletion with password is only supported for email/password accounts.",
        )
    if not verify_password(payload.password, local_identity.password_hash):
        raise HTTPException(status_code=401, detail="Password is incorrect")
    db.delete(user)
    db.commit()
    return {"message": "Account deleted"}