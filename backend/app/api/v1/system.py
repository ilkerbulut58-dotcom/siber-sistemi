"""Public system information for closed pilot operators and testers."""

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.logging import request_id_ctx
from app.schemas.common import APIResponse, ResponseMeta, SystemInfo

router = APIRouter(tags=["system"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


def _short_commit(full: str) -> str:
    return full[:12] if full else ""


@router.get("/system/info", response_model=APIResponse[SystemInfo])
async def system_info(request: Request) -> APIResponse[SystemInfo]:
    settings = get_settings()
    notifications = (
        "disabled (noop)"
        if settings.notifications_provider == "noop"
        else settings.notifications_provider
    )
    return APIResponse(
        data=SystemInfo(
            environment=f"{settings.environment} closed-pilot"
            if settings.environment == "production"
            else settings.environment,
            version=settings.app_version,
            git_commit=_short_commit(settings.git_commit),
            release_tag=settings.release_tag or "none",
            domain_verification_required=not settings.skip_domain_verification,
            scan_daily_quota=settings.scan_daily_quota,
            scan_concurrency_limit=settings.scan_concurrency_limit,
            allowed_profiles=["safe"],
            full_active_enabled=False,
            scan_notifications=notifications,
            public_registration_enabled=settings.public_registration_enabled,
        ),
        meta=_meta(request),
    )
