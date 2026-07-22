"""FastAPI dependencies for authentication and authorization."""

from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.mixins import OrganizationRole, role_at_least
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.services.support_grant_service import SupportGrantService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("UNAUTHORIZED", "Authentication required.", status_code=401)

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise AppError("INVALID_TOKEN", "Invalid or expired token.", status_code=401) from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise AppError("INVALID_TOKEN", "Invalid token type.", status_code=401)

    user_id = payload.get("sub")
    if not user_id:
        raise AppError("INVALID_TOKEN", "Invalid token subject.", status_code=401)

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AppError("UNAUTHORIZED", "User not found or inactive.", status_code=401)
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except AppError:
        return None


async def require_platform_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require the platform operator role without granting invisible tenant access."""
    if not user.is_platform_admin:
        raise AppError("FORBIDDEN", "Platform administrator access is required.", status_code=403)
    return user


async def get_organization_membership(
    org_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMember:
    # System benchmark workspaces are not tenant workspaces, even for their
    # technical owner. They are reachable only through platform quality APIs.
    organization = (
        await db.execute(select(Organization).where(Organization.id == org_id))
    ).scalar_one_or_none()
    if organization is None or not organization.is_active or organization.is_system_scope:
        raise AppError("NOT_FOUND", "Organization not found.", status_code=404)
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is not None:
        return membership

    if user.is_platform_admin:
        grant = await SupportGrantService(db).get_active_grant(
            organization_id=org_id,
            user_id=user.id,
        )
        if grant is not None:
            return OrganizationMember(
                organization_id=org_id,
                user_id=user.id,
                role=OrganizationRole.VIEWER.value,
            )

    raise AppError("FORBIDDEN", "You are not a member of this organization.", status_code=403)


def require_org_role(minimum_role: OrganizationRole):
    async def _checker(
        membership: OrganizationMember = Depends(get_organization_membership),
    ) -> OrganizationMember:
        role = OrganizationRole(membership.role)
        if not role_at_least(role, minimum_role):
            raise AppError("FORBIDDEN", "Insufficient permissions.", status_code=403)
        return membership

    return _checker


async def get_organization(
    org_id: UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    organization = result.scalar_one_or_none()
    if organization is None or not organization.is_active:
        raise AppError("NOT_FOUND", "Organization not found.", status_code=404)
    if organization.is_system_scope:
        raise AppError("NOT_FOUND", "Organization not found.", status_code=404)
    _ = membership
    return organization


def get_client_ip(request: Request) -> str | None:
    settings = get_settings()
    peer_ip = request.client.host if request.client else None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and peer_ip in settings.trusted_proxy_ips:
        return forwarded.split(",")[0].strip()
    return peer_ip
