"""Organization endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_client_ip,
    get_current_user,
    get_organization,
    require_org_role,
)
from app.core.logging import request_id_ctx
from app.models.mixins import OrganizationRole
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.organization import (
    MemberInviteRequest,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.schemas.pilot import OnboardingStatusResponse
from app.services.organization_service import OrganizationService
from app.services.pilot_service import PilotService

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.post(
    "",
    response_model=APIResponse[OrganizationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    data: OrganizationCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[OrganizationResponse]:
    service = OrganizationService(db)
    organization = await service.create(
        user,
        data,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return APIResponse(
        data=OrganizationResponse.model_validate(organization),
        meta=_meta(request),
    )


@router.get("", response_model=APIResponse[list[OrganizationResponse]])
async def list_organizations(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[OrganizationResponse]]:
    service = OrganizationService(db)
    organizations = await service.list_for_user(user)
    return APIResponse(
        data=[OrganizationResponse.model_validate(org) for org in organizations],
        meta=_meta(request),
    )


@router.get("/{org_id}", response_model=APIResponse[OrganizationResponse])
async def get_organization_detail(
    org_id: UUID,
    request: Request,
    organization: Organization = Depends(get_organization),
) -> APIResponse[OrganizationResponse]:
    _ = org_id
    return APIResponse(
        data=OrganizationResponse.model_validate(organization),
        meta=_meta(request),
    )


@router.get("/{org_id}/onboarding-status", response_model=APIResponse[OnboardingStatusResponse])
async def get_onboarding_status(
    org_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_organization),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[OnboardingStatusResponse]:
    _ = org_id
    from sqlalchemy import func, select

    from app.models.domain import Domain
    from app.models.scan import AuthorizationAcceptance

    verified_domains = await db.execute(
        select(func.count())
        .select_from(Domain)
        .where(Domain.organization_id == organization.id, Domain.is_verified.is_(True))
    )
    auth_count = await db.execute(
        select(func.count())
        .select_from(AuthorizationAcceptance)
        .where(AuthorizationAcceptance.organization_id == organization.id)
    )
    status = await PilotService(db).get_onboarding_status(
        organization,
        owner_email_verified=user.is_email_verified,
        verified_domain_count=int(verified_domains.scalar_one()),
        authorization_accepted=int(auth_count.scalar_one()) > 0,
    )
    return APIResponse(data=OnboardingStatusResponse.model_validate(status), meta=_meta(request))


@router.patch("/{org_id}", response_model=APIResponse[OrganizationResponse])
async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_organization),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[OrganizationResponse]:
    _ = org_id
    service = OrganizationService(db)
    updated = await service.update(
        organization,
        data,
        actor=user,
        ip_address=get_client_ip(request),
    )
    return APIResponse(
        data=OrganizationResponse.model_validate(updated),
        meta=_meta(request),
    )


@router.delete("/{org_id}", response_model=APIResponse[dict])
async def delete_organization(
    org_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_organization),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.OWNER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    _ = org_id
    service = OrganizationService(db)
    await service.delete(organization, actor=user, ip_address=get_client_ip(request))
    return APIResponse(data={"message": "Organization deleted."}, meta=_meta(request))


@router.get("/{org_id}/members", response_model=APIResponse[list[OrganizationMemberResponse]])
async def list_members(
    org_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[OrganizationMemberResponse]]:
    service = OrganizationService(db)
    members = await service.list_members(org_id)
    return APIResponse(data=members, meta=_meta(request))


@router.post(
    "/{org_id}/members/invite",
    response_model=APIResponse[OrganizationMemberResponse],
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    org_id: UUID,
    data: MemberInviteRequest,
    request: Request,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_organization),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[OrganizationMemberResponse]:
    _ = org_id
    service = OrganizationService(db)
    member = await service.invite_member(
        organization,
        data,
        actor=user,
        ip_address=get_client_ip(request),
    )
    return APIResponse(data=member, meta=_meta(request))


@router.patch(
    "/{org_id}/members/{member_id}",
    response_model=APIResponse[OrganizationMemberResponse],
)
async def update_member(
    org_id: UUID,
    member_id: UUID,
    data: MemberRoleUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_organization),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[OrganizationMemberResponse]:
    _ = org_id
    service = OrganizationService(db)
    member = await service.update_member_role(
        organization,
        member_id,
        data,
        actor=user,
        ip_address=get_client_ip(request),
    )
    return APIResponse(data=member, meta=_meta(request))


@router.delete("/{org_id}/members/{member_id}", response_model=APIResponse[dict])
async def remove_member(
    org_id: UUID,
    member_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_organization),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    _ = org_id
    service = OrganizationService(db)
    await service.remove_member(
        organization,
        member_id,
        actor=user,
        ip_address=get_client_ip(request),
    )
    return APIResponse(data={"message": "Member removed."}, meta=_meta(request))
