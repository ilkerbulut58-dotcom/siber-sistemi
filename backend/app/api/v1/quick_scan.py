"""Quick scan endpoint — URL gir, taramayı başlat."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_client_ip, get_current_user
from app.core.logging import request_id_ctx
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.quick_scan import QuickScanCreate, QuickScanResponse
from app.services.quick_scan_service import QuickScanService
from app.services.scan_dispatch import dispatch_scan_job

router = APIRouter(prefix="/quick-scan", tags=["quick-scan"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.post("", response_model=APIResponse[QuickScanResponse], status_code=status.HTTP_201_CREATED)
async def start_quick_scan(
    data: QuickScanCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[QuickScanResponse]:
    service = QuickScanService(db)
    result = await service.run(
        data,
        actor=user,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await dispatch_scan_job(result.scan.id, db=db, background_tasks=background_tasks)
    await db.commit()
    return APIResponse(data=result, meta=_meta(request))
