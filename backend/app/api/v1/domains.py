"""Domain API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_client_ip, get_current_user, require_org_role
from app.core.logging import request_id_ctx
from app.models.mixins import OrganizationRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.domain import (
    DomainCreate,
    DomainResponse,
    DomainVerifyResponse,
    VerificationInstructions,
)
from app.services.domain_service import DomainService

router = APIRouter(
    prefix="/organizations/{org_id}/projects/{project_id}/domains",
    tags=["domains"],
)


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.post("", response_model=APIResponse[DomainResponse], status_code=status.HTTP_201_CREATED)
async def add_domain(
    org_id: UUID,
    project_id: UUID,
    data: DomainCreate,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DomainResponse]:
    service = DomainService(db)
    domain, _verification = await service.add(
        org_id, project_id, data, actor=user, ip_address=get_client_ip(request)
    )
    return APIResponse(data=DomainResponse.model_validate(domain), meta=_meta(request))


@router.get("", response_model=APIResponse[list[DomainResponse]])
async def list_domains(
    org_id: UUID,
    project_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[DomainResponse]]:
    service = DomainService(db)
    domains = await service.list_for_project(org_id, project_id)
    return APIResponse(
        data=[DomainResponse.model_validate(d) for d in domains],
        meta=_meta(request),
    )


@router.get("/{domain_id}", response_model=APIResponse[DomainResponse])
async def get_domain(
    org_id: UUID,
    project_id: UUID,
    domain_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DomainResponse]:
    service = DomainService(db)
    domain = await service.get(org_id, project_id, domain_id)
    return APIResponse(data=DomainResponse.model_validate(domain), meta=_meta(request))


@router.delete("/{domain_id}", response_model=APIResponse[dict])
async def delete_domain(
    org_id: UUID,
    project_id: UUID,
    domain_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = DomainService(db)
    domain = await service.get(org_id, project_id, domain_id)
    await service.delete(domain, actor=user, ip_address=get_client_ip(request))
    return APIResponse(data={"message": "Domain removed."}, meta=_meta(request))


@router.get(
    "/{domain_id}/verification-instructions",
    response_model=APIResponse[VerificationInstructions],
)
async def verification_instructions(
    org_id: UUID,
    project_id: UUID,
    domain_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[VerificationInstructions]:
    service = DomainService(db)
    instructions = await service.get_instructions(org_id, project_id, domain_id)
    return APIResponse(data=instructions, meta=_meta(request))


@router.post("/{domain_id}/verify", response_model=APIResponse[DomainVerifyResponse])
async def verify_domain(
    org_id: UUID,
    project_id: UUID,
    domain_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DomainVerifyResponse]:
    service = DomainService(db)
    domain, verified, message = await service.verify(
        org_id, project_id, domain_id, actor=user, ip_address=get_client_ip(request)
    )
    return APIResponse(
        data=DomainVerifyResponse(
            domain=DomainResponse.model_validate(domain),
            verified=verified,
            message=message,
        ),
        meta=_meta(request),
    )
