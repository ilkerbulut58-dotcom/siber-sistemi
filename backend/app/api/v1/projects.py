"""Project API routes."""

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
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/organizations/{org_id}/projects", tags=["projects"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.post("", response_model=APIResponse[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(
    org_id: UUID,
    data: ProjectCreate,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProjectResponse]:
    service = ProjectService(db)
    project = await service.create(org_id, data, actor=user, ip_address=get_client_ip(request))
    return APIResponse(data=ProjectResponse.model_validate(project), meta=_meta(request))


@router.get("", response_model=APIResponse[list[ProjectResponse]])
async def list_projects(
    org_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[ProjectResponse]]:
    service = ProjectService(db)
    projects = await service.list_for_org(org_id)
    return APIResponse(
        data=[ProjectResponse.model_validate(p) for p in projects],
        meta=_meta(request),
    )


@router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def get_project(
    org_id: UUID,
    project_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProjectResponse]:
    service = ProjectService(db)
    project = await service.get(org_id, project_id)
    return APIResponse(data=ProjectResponse.model_validate(project), meta=_meta(request))


@router.patch("/{project_id}", response_model=APIResponse[ProjectResponse])
async def update_project(
    org_id: UUID,
    project_id: UUID,
    data: ProjectUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProjectResponse]:
    service = ProjectService(db)
    project = await service.get(org_id, project_id)
    updated = await service.update(project, data, actor=user, ip_address=get_client_ip(request))
    return APIResponse(data=ProjectResponse.model_validate(updated), meta=_meta(request))


@router.delete("/{project_id}", response_model=APIResponse[dict])
async def delete_project(
    org_id: UUID,
    project_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = ProjectService(db)
    project = await service.get(org_id, project_id)
    await service.delete(project, actor=user, ip_address=get_client_ip(request))
    return APIResponse(data={"message": "Project deleted."}, meta=_meta(request))
