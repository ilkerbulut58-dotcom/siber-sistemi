"""Authentication business logic."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import EmailVerificationToken, PasswordResetToken, RefreshToken, User
from app.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    normalize_login_email,
)
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
EMAIL_VERIFY_HOURS = 24
PASSWORD_RESET_HOURS = 1


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def register(
        self,
        data: RegisterRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[TokenResponse, AuthUserResponse, str]:
        existing = await self.db.execute(select(User).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise AppError(
                "EMAIL_EXISTS",
                "An account with this email already exists.",
                status_code=409,
            )

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        self.db.add(user)
        await self.db.flush()

        verify_token = await self._create_email_verification_token(user.id)
        tokens = await self._issue_tokens(user)

        await log_audit_event(
            self.db,
            action="user.registered",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("User registered: %s (verification token logged in dev)", user.email)
        if self.settings.is_development:
            logger.info("Email verification token for %s: %s", user.email, verify_token)

        return tokens, AuthUserResponse.model_validate(user), verify_token

    async def login(
        self,
        data: LoginRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[TokenResponse, AuthUserResponse]:
        result = await self.db.execute(
            select(User).where(User.email == normalize_login_email(data.email))
        )
        user = result.scalar_one_or_none()

        if user is None or not verify_password(data.password, user.password_hash):
            if user is not None:
                await self._record_failed_login(user)
            raise AppError("INVALID_CREDENTIALS", "Invalid email or password.", status_code=401)

        if user.locked_until and _ensure_utc(user.locked_until) > datetime.now(UTC):
            raise AppError(
                "ACCOUNT_LOCKED",
                "Account temporarily locked. Try again later.",
                status_code=423,
            )

        if not user.is_active:
            raise AppError("ACCOUNT_INACTIVE", "Account is inactive.", status_code=403)

        user.failed_login_count = 0
        user.locked_until = None
        tokens = await self._issue_tokens(user)

        await log_audit_event(
            self.db,
            action="user.login",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return tokens, AuthUserResponse.model_validate(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        from app.core.security import decode_token

        try:
            payload = decode_token(refresh_token)
        except Exception as exc:
            raise AppError("INVALID_TOKEN", "Invalid refresh token.", status_code=401) from exc

        if payload.get("type") != TOKEN_TYPE_REFRESH:
            raise AppError("INVALID_TOKEN", "Invalid token type.", status_code=401)

        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored is None or stored.revoked_at is not None:
            raise AppError("INVALID_TOKEN", "Refresh token revoked or not found.", status_code=401)
        if _ensure_utc(stored.expires_at) <= datetime.now(UTC):
            raise AppError("INVALID_TOKEN", "Refresh token expired.", status_code=401)

        stored.revoked_at = datetime.now(UTC)
        user_result = await self.db.execute(select(User).where(User.id == stored.user_id))
        user = user_result.scalar_one()
        if not user.is_active:
            raise AppError("ACCOUNT_INACTIVE", "Account is inactive.", status_code=403)

        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str, *, user_id: UUID) -> None:
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
            )
        )
        stored = result.scalar_one_or_none()
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)

    async def verify_email(self, token: str) -> AuthUserResponse:
        token_hash = hash_token(token)
        result = await self.db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        record = result.scalar_one_or_none()
        if record is None or record.used_at is not None:
            raise AppError("INVALID_TOKEN", "Invalid verification token.", status_code=400)
        if _ensure_utc(record.expires_at) <= datetime.now(UTC):
            raise AppError("TOKEN_EXPIRED", "Verification token expired.", status_code=400)

        user_result = await self.db.execute(select(User).where(User.id == record.user_id))
        user = user_result.scalar_one()
        user.is_email_verified = True
        record.used_at = datetime.now(UTC)
        return AuthUserResponse.model_validate(user)

    async def resend_verification(self, user: User) -> str:
        if user.is_email_verified:
            raise AppError("ALREADY_VERIFIED", "Email is already verified.", status_code=400)
        token = await self._create_email_verification_token(user.id)
        if self.settings.is_development:
            logger.info("Email verification token for %s: %s", user.email, token)
        return token

    async def forgot_password(self, email: str) -> str | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if user is None:
            return None

        token = generate_opaque_token()
        record = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=PASSWORD_RESET_HOURS),
        )
        self.db.add(record)
        if self.settings.is_development:
            logger.info("Password reset token for %s: %s", user.email, token)
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        token_hash = hash_token(token)
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        record = result.scalar_one_or_none()
        if record is None or record.used_at is not None:
            raise AppError("INVALID_TOKEN", "Invalid reset token.", status_code=400)
        if _ensure_utc(record.expires_at) <= datetime.now(UTC):
            raise AppError("TOKEN_EXPIRED", "Reset token expired.", status_code=400)

        user_result = await self.db.execute(select(User).where(User.id == record.user_id))
        user = user_result.scalar_one()
        user.password_hash = hash_password(new_password)
        user.failed_login_count = 0
        user.locked_until = None
        record.used_at = datetime.now(UTC)

        revoke_result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for refresh in revoke_result.scalars():
            refresh.revoked_at = datetime.now(UTC)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(user.id)
        refresh_token, expires_at = create_refresh_token(user.id)
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=expires_at,
            )
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_expire_minutes * 60,
        )

    async def _create_email_verification_token(self, user_id: UUID) -> str:
        token = generate_opaque_token()
        self.db.add(
            EmailVerificationToken(
                user_id=user_id,
                token_hash=hash_token(token),
                expires_at=datetime.now(UTC) + timedelta(hours=EMAIL_VERIFY_HOURS),
            )
        )
        return token

    async def _record_failed_login(self, user: User) -> None:
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)
