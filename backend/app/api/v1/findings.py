"""Finding API routes."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_client_ip, get_current_user, require_org_role
from app.core.logging import request_id_ctx
from app.models.mixins import OrganizationRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.finding import FindingHistoryResponse, FindingResponse, FindingUpdate
from app.schemas.scan import ScanResponse
from app.security.evidence_sanitizer import sanitize_history_details
from app.services.finding_response_builder import to_finding_response
from app.services.finding_service import FindingService
from app.services.scan_dispatch import dispatch_scan_job

router = APIRouter(prefix="/organizations/{org_id}/findings", tags=["findings"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


def _history_response(entry) -> FindingHistoryResponse:
    data = FindingHistoryResponse.model_validate(entry)
    return data.model_copy(update={"details": sanitize_history_details(data.details)})


@router.get("", response_model=APIResponse[list[FindingResponse]])
async def list_findings(
    org_id: UUID,
    request: Request,
    project_id: UUID | None = Query(default=None),
    scan_id: UUID | None = Query(default=None),
    severity: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    mobile_application_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[FindingResponse]]:
    service = FindingService(db)
    findings = await service.list_for_org(
        org_id,
        project_id=project_id,
        scan_id=scan_id,
        severity=severity,
        asset_type=asset_type,
        mobile_application_id=mobile_application_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        data=[to_finding_response(f) for f in findings],
        meta=_meta(request),
    )


@router.get("/{finding_id}", response_model=APIResponse[FindingResponse])
async def get_finding(
    org_id: UUID,
    finding_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[FindingResponse]:
    service = FindingService(db)
    finding = await service.get(org_id, finding_id)
    return APIResponse(data=to_finding_response(finding), meta=_meta(request))


@router.patch("/{finding_id}", response_model=APIResponse[FindingResponse])
async def update_finding(
    org_id: UUID,
    finding_id: UUID,
    data: FindingUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[FindingResponse]:
    service = FindingService(db)
    finding = await service.get(org_id, finding_id)
    updated = await service.update(
        finding,
        data,
        actor=user,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()
    await db.refresh(updated)
    return APIResponse(data=to_finding_response(updated), meta=_meta(request))


@router.get("/{finding_id}/history", response_model=APIResponse[list[FindingHistoryResponse]])
async def finding_history(
    org_id: UUID,
    finding_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[FindingHistoryResponse]]:
    service = FindingService(db)
    history = await service.list_history(org_id, finding_id)
    return APIResponse(
        data=[_history_response(h) for h in history],
        meta=_meta(request),
    )


@router.post("/{finding_id}/retest", response_model=APIResponse[ScanResponse])
async def retest_finding(
    org_id: UUID,
    finding_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanResponse]:
    service = FindingService(db)
    scan = await service.retest(
        org_id,
        finding_id,
        actor=user,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await dispatch_scan_job(scan.id, db=db, background_tasks=background_tasks)
    await db.commit()
    return APIResponse(data=ScanResponse.model_validate(scan), meta=_meta(request))
