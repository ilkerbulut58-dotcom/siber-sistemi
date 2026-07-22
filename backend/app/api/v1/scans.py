"""Scan API routes."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_client_ip, get_current_user, require_org_role
from app.core.logging import request_id_ctx
from app.models.mixins import OrganizationRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.scan import ScanCreate, ScanProfileResponse, ScanResponse, ScanStatusResponse
from app.schemas.site_profile import SiteProfileResponse
from app.services.report_service import ReportService
from app.services.scan_dispatch import dispatch_scan_job
from app.services.scan_service import ScanService
from app.services.site_profile_service import SiteProfileService

router = APIRouter(tags=["scans"])
profiles_router = APIRouter(prefix="/scan-profiles", tags=["scan-profiles"])
org_scans_router = APIRouter(prefix="/organizations/{org_id}/scans", tags=["scans"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@profiles_router.get("", response_model=APIResponse[list[ScanProfileResponse]])
async def list_scan_profiles(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[ScanProfileResponse]]:
    _ = user
    service = ScanService(db)
    profiles = await service.list_profiles()
    return APIResponse(
        data=[ScanProfileResponse.model_validate(p) for p in profiles],
        meta=_meta(request),
    )


@profiles_router.get("/{name}", response_model=APIResponse[ScanProfileResponse])
async def get_scan_profile(
    name: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanProfileResponse]:
    _ = user
    service = ScanService(db)
    profile = await service.get_profile(name)
    return APIResponse(data=ScanProfileResponse.model_validate(profile), meta=_meta(request))


@org_scans_router.post("", response_model=APIResponse[ScanResponse], status_code=status.HTTP_201_CREATED)
async def start_scan(
    org_id: UUID,
    data: ScanCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.SECURITY_ANALYST)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanResponse]:
    service = ScanService(db)
    scan = await service.create(
        org_id,
        data,
        actor=user,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await dispatch_scan_job(scan.id, db=db, background_tasks=background_tasks)
    await db.commit()
    return APIResponse(data=ScanResponse.model_validate(scan), meta=_meta(request))


@org_scans_router.get("", response_model=APIResponse[list[ScanResponse]])
async def list_scans(
    org_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[ScanResponse]]:
    service = ScanService(db)
    scans = await service.list_for_org(org_id)
    return APIResponse(
        data=[ScanResponse.model_validate(s) for s in scans],
        meta=_meta(request),
    )


@org_scans_router.get("/{scan_id}", response_model=APIResponse[ScanResponse])
async def get_scan(
    org_id: UUID,
    scan_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanResponse]:
    service = ScanService(db)
    scan = await service.get(org_id, scan_id)
    return APIResponse(data=ScanResponse.model_validate(scan), meta=_meta(request))


@org_scans_router.get("/{scan_id}/status", response_model=APIResponse[ScanStatusResponse])
async def get_scan_status(
    org_id: UUID,
    scan_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanStatusResponse]:
    service = ScanService(db)
    scan = await service.get(org_id, scan_id)
    return APIResponse(
        data=ScanStatusResponse.model_validate(scan),
        meta=_meta(request),
    )


@org_scans_router.get("/{scan_id}/site-profile", response_model=APIResponse[SiteProfileResponse])
async def get_scan_site_profile(
    org_id: UUID,
    scan_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SiteProfileResponse]:
    profile = await SiteProfileService(db).get_for_scan(org_id, scan_id)
    if profile is None:
        from app.core.exceptions import AppError

        raise AppError("NOT_FOUND", "Site profile not available for this scan yet.", status_code=404)
    return APIResponse(data=profile, meta=_meta(request))


@org_scans_router.get("/{scan_id}/report")
async def download_scan_report(
    org_id: UUID,
    scan_id: UUID,
    request: Request,
    report_format: str = Query(default="html", alias="format", pattern="^(html|pdf|json)$"),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = ReportService(db)
    content, media_type, filename = await service.build(org_id, scan_id, report_format)  # type: ignore[arg-type]
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@org_scans_router.post("/{scan_id}/cancel", response_model=APIResponse[ScanResponse])
async def cancel_scan(
    org_id: UUID,
    scan_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.SECURITY_ANALYST)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanResponse]:
    service = ScanService(db)
    scan = await service.cancel(org_id, scan_id, actor=user)
    return APIResponse(data=ScanResponse.model_validate(scan), meta=_meta(request))
