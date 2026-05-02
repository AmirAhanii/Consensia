from pydantic import BaseModel, EmailStr, Field, model_validator

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token from frontend

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_email_verified: bool
    auth_provider: str
    is_admin: bool = False

class VerifyEmailCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)

class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyPasswordResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Current password to confirm account deletion")