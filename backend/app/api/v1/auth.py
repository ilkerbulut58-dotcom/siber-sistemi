"""Authentication endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_client_ip, get_current_user
from app.core.logging import request_id_ctx
from app.models.user import User
from app.schemas.auth import (
    AuthUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import APIResponse, ResponseMeta
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.post("/register", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = AuthService(db)
    tokens, user, verify_token = await service.register(
        data,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    payload: dict = {
        "tokens": tokens.model_dump(),
        "user": user.model_dump(),
    }
    from app.core.config import get_settings

    if get_settings().is_development:
        payload["email_verification_token"] = verify_token
    return APIResponse(data=payload, meta=_meta(request))


@router.post("/login", response_model=APIResponse[dict])
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = AuthService(db)
    tokens, user = await service.login(
        data,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return APIResponse(
        data={"tokens": tokens.model_dump(), "user": user.model_dump()},
        meta=_meta(request),
    )


@router.post("/logout", response_model=APIResponse[dict])
async def logout(
    data: RefreshRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = AuthService(db)
    await service.logout(data.refresh_token, user_id=user.id)
    return APIResponse(data={"message": "Logged out successfully."}, meta=_meta(request))


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    data: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    service = AuthService(db)
    tokens = await service.refresh(data.refresh_token)
    return APIResponse(data=tokens, meta=_meta(request))


@router.post("/verify-email", response_model=APIResponse[AuthUserResponse])
async def verify_email(
    data: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AuthUserResponse]:
    service = AuthService(db)
    user = await service.verify_email(data.token)
    return APIResponse(data=user, meta=_meta(request))


@router.post("/resend-verification", response_model=APIResponse[dict])
async def resend_verification(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = AuthService(db)
    token = await service.resend_verification(user)
    payload: dict = {"message": "Verification email sent."}
    from app.core.config import get_settings

    if get_settings().is_development:
        payload["email_verification_token"] = token
    return APIResponse(data=payload, meta=_meta(request))


@router.post("/forgot-password", response_model=APIResponse[dict])
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = AuthService(db)
    token = await service.forgot_password(data.email)
    payload: dict = {
        "message": "If an account exists, a password reset link has been sent.",
    }
    from app.core.config import get_settings

    if get_settings().is_development and token:
        payload["password_reset_token"] = token
    return APIResponse(data=payload, meta=_meta(request))


@router.post("/reset-password", response_model=APIResponse[dict])
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = AuthService(db)
    await service.reset_password(data.token, data.new_password)
    return APIResponse(data={"message": "Password reset successfully."}, meta=_meta(request))


@router.get("/me", response_model=APIResponse[AuthUserResponse])
async def auth_me(
    request: Request,
    user: User = Depends(get_current_user),
) -> APIResponse[AuthUserResponse]:
    return APIResponse(data=AuthUserResponse.model_validate(user), meta=_meta(request))
