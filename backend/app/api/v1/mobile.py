"""Mobile application security API routes."""

from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_client_ip, get_current_user, require_org_role
from app.core.exceptions import AppError
from app.core.logging import request_id_ctx
from app.mobile.services.mobile_dispatch import dispatch_mobile_analysis
from app.mobile.services.mobile_service import MobileService
from app.models.mixins import OrganizationRole
from app.models.mobile_application import MobileAnalysisStatus
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.finding import FindingResponse
from app.schemas.mobile import MobileApplicationResponse, MobileApplicationUploadResponse
from app.services.finding_response_builder import to_finding_response
from app.services.finding_service import FindingService
from app.services.mobile_report_service import MobileReportService

router = APIRouter(prefix="/organizations/{org_id}/mobile", tags=["mobile"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


def _app_response(app, *, duplicate: bool = False) -> MobileApplicationUploadResponse:
    return MobileApplicationUploadResponse(
        id=app.id,
        organization_id=app.organization_id,
        project_id=app.project_id,
        platform=app.platform,
        application_name=app.application_name,
        package_name=app.package_name,
        version_name=app.version_name,
        version_code=app.version_code,
        environment=app.environment,
        original_filename=app.original_filename,
        file_size=app.file_size,
        sha256=app.sha256,
        upload_status=app.upload_status,
        analysis_status=app.analysis_status,
        security_score=app.security_score,
        findings_count=app.findings_count,
        analysis_summary=app.analysis_summary,
        duplicate=duplicate,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.post(
    "/applications",
    response_model=APIResponse[MobileApplicationUploadResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_mobile_application(
    org_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: UUID = Form(...),
    environment: str = Form(default="staging"),
    authorization_accepted: str = Form(default="false"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.DEVELOPER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MobileApplicationUploadResponse]:
    if authorization_accepted.lower() not in {"true", "1", "yes", "on"}:
        raise AppError(
            "AUTHORIZATION_REQUIRED",
            "You must confirm authorization to analyze this application.",
            status_code=400,
        )
    declared_size = request.headers.get("Content-Length")
    if declared_size and declared_size.isdigit() and int(declared_size) > get_settings().mobile_max_upload_bytes + (
        1024 * 1024
    ):
        raise AppError("FILE_TOO_LARGE", "Upload exceeds the configured maximum size.", status_code=400)
    if file.content_type and file.content_type.startswith("text/"):
        raise AppError("INVALID_APK", "Upload must be an Android APK archive.", status_code=400)
    service = MobileService(db)
    app, duplicate = await service.upload_apk_stream(
        org_id,
        project_id,
        filename=file.filename or "upload.apk",
        upload=file,
        environment=environment,
        actor=user,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    if not duplicate:
        await db.commit()
        try:
            await dispatch_mobile_analysis(app.id, db=db, background_tasks=background_tasks)
        except Exception:
            app.analysis_status = MobileAnalysisStatus.FAILED
            app.error_log = "Isolated mobile analysis dispatch is unavailable."
            await db.commit()
            raise
        await db.commit()
    else:
        await db.commit()
    await db.refresh(app)
    return APIResponse(
        data=_app_response(app, duplicate=duplicate),
        meta=_meta(request),
    )


@router.get("/applications", response_model=APIResponse[list[MobileApplicationResponse]])
async def list_mobile_applications(
    org_id: UUID,
    request: Request,
    project_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[MobileApplicationResponse]]:
    service = MobileService(db)
    apps = await service.list_for_org(
        org_id,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        data=[MobileApplicationResponse.model_validate(a) for a in apps],
        meta=_meta(request),
    )


@router.get("/applications/{app_id}", response_model=APIResponse[MobileApplicationResponse])
async def get_mobile_application(
    org_id: UUID,
    app_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MobileApplicationResponse]:
    service = MobileService(db)
    app = await service.get(org_id, app_id)
    return APIResponse(
        data=MobileApplicationResponse.model_validate(app),
        meta=_meta(request),
    )


@router.get(
    "/applications/{app_id}/findings",
    response_model=APIResponse[list[FindingResponse]],
)
async def list_mobile_findings(
    org_id: UUID,
    app_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[FindingResponse]]:
    service = MobileService(db)
    app = await service.get(org_id, app_id)
    findings = await FindingService(db).list_for_org(
        org_id,
        project_id=app.project_id,
        mobile_application_id=app.id,
        asset_type="mobile",
    )
    return APIResponse(
        data=[to_finding_response(f) for f in findings],
        meta=_meta(request),
    )


@router.get("/applications/{app_id}/report")
async def get_mobile_report(
    org_id: UUID,
    app_id: UUID,
    request: Request,
    report_format: str = Query(default="json", alias="format", pattern="^(html|pdf|json)$"),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = MobileReportService(db)
    content, media_type, filename = await service.build(org_id, app_id, report_format)  # type: ignore[arg-type]
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
