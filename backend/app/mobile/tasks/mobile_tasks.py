"""Celery tasks for mobile application security analysis."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.mobile.services.mobile_service import MobileService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    name="siber.run_mobile_analysis",
    bind=True,
    max_retries=0,
    time_limit=settings.mobile_analysis_timeout_seconds,
    soft_time_limit=max(settings.mobile_analysis_timeout_seconds - 30, 1),
)
def run_mobile_analysis_task(self, app_id: str) -> dict[str, str]:
    logger.info("Celery worker starting mobile analysis %s", app_id)

    async def _run() -> None:
        async with async_session_factory() as db:
            await MobileService(db).run_analysis(UUID(app_id))

    asyncio.run(_run())
    return {"app_id": app_id, "status": "finished"}
