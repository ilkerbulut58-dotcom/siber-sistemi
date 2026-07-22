"""Authentication request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


def normalize_login_email(value: str) -> str:
    """Map short usernames like 'admin' to login email."""
    v = value.strip().lower()
    if v == "admin":
        return "admin@admin.com"
    if "@" not in v:
        return f"{v}@admin.com"
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    is_email_verified: bool
    is_platform_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}
