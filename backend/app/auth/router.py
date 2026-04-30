from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from .deps import get_current_user_id
from .emailer import send_verification_email_if_configured
from .google_auth import verify_google_credential
from .repository import (
    create_email_verification_code,
    create_google_identity,
    create_local_identity,
    create_user,
    get_active_verification_code,
    get_local_identity,
    get_user_by_email,
    get_user_by_google_sub,
    get_user_by_id,
    invalidate_unused_verification_codes,
    mark_email_verified,
)
from .schemas import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    VerifyEmailCodeRequest,
)
from .security import (
    create_access_token,
    hash_password,
    hash_verification_code,
    new_email_verification_code,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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

        try:
            sent = send_verification_email_if_configured(
                settings.smtp_host,
                settings.smtp_port,
                settings.smtp_user,
                settings.smtp_password,
                settings.mail_from,
                existing.email,
                raw_code,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Account exists but verification email could not be sent: {exc}",
            ) from exc

        if sent:
            msg = "Account already exists but is not verified. A new verification code has been sent."
        else:
            msg = (
                "Account exists but is not verified. SMTP is not configured — "
                "check backend logs for your new verification code, then verify on the next page."
            )
        return {"message": msg}

    password_hash = hash_password(payload.password)
    raw_code, code_hash = new_email_verification_code()
    expires_at = utcnow() + timedelta(hours=24)

    user = create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        is_email_verified=False,
    )

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

    try:
        sent = send_verification_email_if_configured(
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_user,
            settings.smtp_password,
            settings.mail_from,
            user.email,
            raw_code,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"User was created, but verification email could not be sent: {exc}",
        ) from exc

    if sent:
        msg = "Registration successful. Check your email for the verification code."
    else:
        msg = (
            "Registration successful. SMTP is not configured — "
            "check backend logs for your verification code, then continue to the verify page."
        )
    return {"message": msg}


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

    try:
        sent = send_verification_email_if_configured(
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_user,
            settings.smtp_password,
            settings.mail_from,
            user.email,
            raw_code,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Verification email could not be sent: {exc}",
        ) from exc

    if sent:
        msg = "A new verification code has been sent."
    else:
        msg = (
            "SMTP is not configured — check backend logs for your new verification code "
            "and enter it on the verify page."
        )
    return {"message": msg}


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    local_identity = get_local_identity(db, user.id)
    if not local_identity or not local_identity.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")

    if not verify_password(payload.password, local_identity.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

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
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
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