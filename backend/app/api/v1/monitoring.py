"""Monitoring API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_org_role
from app.core.logging import request_id_ctx
from app.models.mixins import OrganizationRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.common import APIResponse, ResponseMeta
from app.schemas.monitoring import (
    MonitoringEventResponse,
    ScanScheduleCreate,
    ScanScheduleResponse,
    ScanScheduleUpdate,
)
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/organizations/{org_id}/monitoring", tags=["monitoring"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.get("/schedules", response_model=APIResponse[list[ScanScheduleResponse]])
async def list_schedules(
    org_id: UUID,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[ScanScheduleResponse]]:
    schedules = await MonitoringService(db).list_schedules(org_id)
    return APIResponse(
        data=[ScanScheduleResponse.model_validate(s) for s in schedules],
        meta=_meta(request),
    )


@router.post(
    "/schedules",
    response_model=APIResponse[ScanScheduleResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    org_id: UUID,
    data: ScanScheduleCreate,
    request: Request,
    user: User = Depends(get_current_user),
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.SECURITY_ANALYST)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanScheduleResponse]:
    schedule = await MonitoringService(db).create_schedule(org_id, data, actor=user)
    return APIResponse(data=ScanScheduleResponse.model_validate(schedule), meta=_meta(request))


@router.patch("/schedules/{schedule_id}", response_model=APIResponse[ScanScheduleResponse])
async def update_schedule(
    org_id: UUID,
    schedule_id: UUID,
    data: ScanScheduleUpdate,
    request: Request,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.SECURITY_ANALYST)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ScanScheduleResponse]:
    schedule = await MonitoringService(db).update_schedule(org_id, schedule_id, data)
    return APIResponse(data=ScanScheduleResponse.model_validate(schedule), meta=_meta(request))


@router.get("/events", response_model=APIResponse[list[MonitoringEventResponse]])
async def list_monitoring_events(
    org_id: UUID,
    request: Request,
    schedule_id: UUID | None = None,
    _membership: OrganizationMember = Depends(require_org_role(OrganizationRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[MonitoringEventResponse]]:
    events = await MonitoringService(db).list_events(org_id, schedule_id=schedule_id)
    return APIResponse(
        data=[MonitoringEventResponse.model_validate(e) for e in events],
        meta=_meta(request),
    )
