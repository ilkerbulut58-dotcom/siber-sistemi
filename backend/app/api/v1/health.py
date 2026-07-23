"""Health check endpoints."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import check_database_connection
from app.core.logging import request_id_ctx
from app.core.redis import check_redis_connection
from app.schemas.common import APIResponse, HealthStatus, ReadinessStatus, ResponseMeta

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id_ctx.get() or getattr(request.state, "request_id", "")
    )


@router.get("/health", response_model=APIResponse[HealthStatus])
async def health_check(request: Request) -> APIResponse[HealthStatus]:
    settings = get_settings()
    return APIResponse(
        data=HealthStatus(
            status="healthy",
            version=settings.app_version,
            environment=settings.environment,
            skip_domain_verification=settings.skip_domain_verification,
        ),
        meta=_meta(request),
    )


@router.get("/health/live", response_model=APIResponse[HealthStatus])
async def liveness_probe(request: Request) -> APIResponse[HealthStatus]:
    settings = get_settings()
    return APIResponse(
        data=HealthStatus(
            status="alive",
            version=settings.app_version,
            environment=settings.environment,
            skip_domain_verification=settings.skip_domain_verification,
        ),
        meta=_meta(request),
    )


@router.get("/health/ready", response_model=APIResponse[ReadinessStatus])
async def readiness_probe(request: Request) -> APIResponse[ReadinessStatus]:
    settings = get_settings()

    db_ok = await check_database_connection()
    redis_ok = await check_redis_connection()

    checks = {
        "database": "ok" if db_ok else "failed",
        "redis": "ok" if redis_ok else "failed",
    }

    all_ok = db_ok and redis_ok
    status = "ready" if all_ok else "not_ready"

    if not all_ok:
        logger.warning("Readiness check failed", extra={"checks": checks})

    payload = APIResponse(
        success=all_ok,
        data=ReadinessStatus(
            status=status,
            version=settings.app_version,
            environment=settings.environment,
            checks=checks,
        ),
        meta=_meta(request),
    )
    if not all_ok:
        return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
    return payload
