"""Attack Surface Management API routes."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_org_role
from app.core.logging import request_id_ctx
from app.models.mixins import OrganizationRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.asm import (
    AsmDiscoverCreate,
    AsmDiscoveryJobResponse,
    AssetResponse,
    AttackSurfaceSummary,
)
from app.schemas.common import APIResponse, ResponseMeta
from app.services.asm_dispatch import dispatch_asm_discovery
from app.services.asm_service import AsmService

router = APIRouter(
    prefix="/organizations/{org_id}/projects/{project_id}/asm",
    tags=["asm"],
)


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


def _asset_response(asset) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        organization_id=asset.organization_id,
        project_id=asset.project_id,
        domain_id=asset.domain_id,
        discovery_job_id=asset.discovery_job_id,
        parent_asset_id=asset.parent_asset_id,
        asset_type=asset.asset_type,
        identifier=asset.identifier,
        url=asset.url,
        status=asset.status,
        metadata=asset.metadata_,
        exposure_score=asset.exposure_score,
        risk_score=asset.risk_score,
        first_seen_at=asset.first_seen_at,
        last_seen_at=asset.last_seen_at,
        last_scanned_at=asset.last_scanned_at,
    )


@router.post(
    "/discover",
    response_model=APIResponse[AsmDiscoveryJobResponse],
    status_code=status.HTTP_201_CREATED,
)
async def start_asm_discovery(
    org_id: UUID,
    project_id: UUID,
    data: AsmDiscoverCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.SECURITY_ANALYST)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AsmDiscoveryJobResponse]:
    service = AsmService(db)
    job = await service.create_discovery(org_id, project_id, data, actor=user)
    await db.commit()
    await dispatch_asm_discovery(job.id, db=db, background_tasks=background_tasks)
    await db.commit()
    return APIResponse(
        data=AsmDiscoveryJobResponse.model_validate(job),
        meta=_meta(request),
    )


@router.get("/jobs", response_model=APIResponse[list[AsmDiscoveryJobResponse]])
async def list_asm_jobs(
    org_id: UUID,
    project_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[AsmDiscoveryJobResponse]]:
    service = AsmService(db)
    jobs = await service.list_jobs(org_id, project_id)
    return APIResponse(
        data=[AsmDiscoveryJobResponse.model_validate(j) for j in jobs],
        meta=_meta(request),
    )


@router.get("/jobs/{job_id}", response_model=APIResponse[AsmDiscoveryJobResponse])
async def get_asm_job(
    org_id: UUID,
    project_id: UUID,
    job_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AsmDiscoveryJobResponse]:
    service = AsmService(db)
    job = await service.get_job(org_id, project_id, job_id)
    return APIResponse(data=AsmDiscoveryJobResponse.model_validate(job), meta=_meta(request))


@router.get("/assets", response_model=APIResponse[list[AssetResponse]])
async def list_assets(
    org_id: UUID,
    project_id: UUID,
    request: Request,
    domain_id: UUID | None = None,
    asset_type: str | None = None,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[AssetResponse]]:
    service = AsmService(db)
    assets = await service.list_assets(org_id, project_id, domain_id=domain_id, asset_type=asset_type)
    return APIResponse(
        data=[_asset_response(a) for a in assets],
        meta=_meta(request),
    )


@router.get("/surface", response_model=APIResponse[AttackSurfaceSummary])
async def get_attack_surface(
    org_id: UUID,
    project_id: UUID,
    request: Request,
    domain_id: UUID | None = None,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AttackSurfaceSummary]:
    service = AsmService(db)
    summary = await service.get_surface_summary(org_id, project_id, domain_id=domain_id)
    return APIResponse(data=summary, meta=_meta(request))
