"""User profile endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_client_ip, get_current_user
from app.core.logging import request_id_ctx
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.user import PasswordChangeRequest, UserProfileResponse, UserProfileUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.get("/me", response_model=APIResponse[UserProfileResponse])
async def get_profile(
    request: Request,
    user: User = Depends(get_current_user),
) -> APIResponse[UserProfileResponse]:
    return APIResponse(data=UserProfileResponse.model_validate(user), meta=_meta(request))


@router.patch("/me", response_model=APIResponse[UserProfileResponse])
async def update_profile(
    data: UserProfileUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UserProfileResponse]:
    service = UserService(db)
    updated = await service.update_profile(user, data)
    return APIResponse(data=UserProfileResponse.model_validate(updated), meta=_meta(request))


@router.patch("/me/password", response_model=APIResponse[dict])
async def change_password(
    data: PasswordChangeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = UserService(db)
    await service.change_password(user, data, ip_address=get_client_ip(request))
    return APIResponse(data={"message": "Password updated successfully."}, meta=_meta(request))
