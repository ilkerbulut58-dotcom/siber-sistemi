"""Platform-operator endpoints.

These routes intentionally manage only operator-owned workspaces. They do not
provide an unlogged bypass into customer organizations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_client_ip, require_platform_admin
from app.core.logging import request_id_ctx
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.benchmark import BenchmarkRunResponse, QualitySummaryResponse
from app.schemas.organization import OrganizationCreate, OrganizationResponse
from app.schemas.support_grant import SupportGrantCreate, SupportGrantResponse
from app.services.organization_service import OrganizationService
from app.services.support_grant_service import SupportGrantService
from app.services.benchmark_quality_service import BenchmarkQualityService

router = APIRouter(prefix="/platform", tags=["platform"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.get(
    "/managed-workspaces",
    response_model=APIResponse[list[OrganizationResponse]],
)
async def list_managed_workspaces(
    request: Request,
    _platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[OrganizationResponse]]:
    workspaces = await OrganizationService(db).list_managed_workspaces()
    return APIResponse(
        data=[OrganizationResponse.model_validate(workspace) for workspace in workspaces],
        meta=_meta(request),
    )


@router.post(
    "/managed-workspaces",
    response_model=APIResponse[OrganizationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_managed_workspace(
    data: OrganizationCreate,
    request: Request,
    platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[OrganizationResponse]:
    workspace = await OrganizationService(db).create_managed_workspace(
        platform_admin,
        data,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return APIResponse(
        data=OrganizationResponse.model_validate(workspace),
        meta=_meta(request),
    )


@router.get(
    "/customer-organizations",
    response_model=APIResponse[list[OrganizationResponse]],
)
async def list_customer_organizations(
    request: Request,
    _platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[OrganizationResponse]]:
    from sqlalchemy import select

    from app.models.organization import Organization

    result = await db.execute(
        select(Organization)
        .where(
            Organization.is_active.is_(True),
            Organization.is_managed_workspace.is_(False),
                Organization.is_system_scope.is_(False),
        )
        .order_by(Organization.name)
    )
    organizations = list(result.scalars())
    return APIResponse(
        data=[OrganizationResponse.model_validate(org) for org in organizations],
        meta=_meta(request),
    )


@router.get(
    "/support-grants",
    response_model=APIResponse[list[SupportGrantResponse]],
)
async def list_support_grants(
    request: Request,
    active_only: bool = True,
    organization_id: UUID | None = None,
    _platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[SupportGrantResponse]]:
    grants = await SupportGrantService(db).list_grants(
        active_only=active_only,
        organization_id=organization_id,
    )
    return APIResponse(data=grants, meta=_meta(request))


@router.post(
    "/support-grants",
    response_model=APIResponse[SupportGrantResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_support_grant(
    data: SupportGrantCreate,
    request: Request,
    platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SupportGrantResponse]:
    grant = await SupportGrantService(db).create(
        actor=platform_admin,
        data=data,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return APIResponse(data=grant, meta=_meta(request))


@router.delete(
    "/support-grants/{grant_id}",
    response_model=APIResponse[SupportGrantResponse],
)
async def revoke_support_grant(
    grant_id: UUID,
    request: Request,
    platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SupportGrantResponse]:
    grant = await SupportGrantService(db).revoke(
        grant_id=grant_id,
        actor=platform_admin,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return APIResponse(data=grant, meta=_meta(request))


@router.get("/quality/summary", response_model=APIResponse[QualitySummaryResponse])
async def quality_summary(
    request: Request,
    _platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[QualitySummaryResponse]:
    return APIResponse(data=await BenchmarkQualityService(db).summary(), meta=_meta(request))


@router.get("/quality/runs", response_model=APIResponse[list[BenchmarkRunResponse]])
async def quality_runs(
    request: Request,
    limit: int = 30,
    _platform_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[BenchmarkRunResponse]]:
    from sqlalchemy import select
    from app.models.benchmark import BenchmarkRun

    result = await db.execute(
        select(BenchmarkRun).order_by(BenchmarkRun.created_at.desc()).limit(min(limit, 100))
    )
    return APIResponse(
        data=[BenchmarkRunResponse.model_validate(run) for run in result.scalars()],
        meta=_meta(request),
    )
