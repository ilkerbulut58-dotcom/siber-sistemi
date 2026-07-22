"""Dispatch mobile analysis jobs to Celery or inline execution."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.exceptions import AppError
from app.mobile.services.mobile_service import MobileService
from app.models.mobile_application import MobileApplication

logger = logging.getLogger(__name__)


async def dispatch_mobile_analysis(
    app_id: UUID,
    *,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
    session_factory: async_sessionmaker | None = None,
) -> None:
    settings = get_settings()
    factory = session_factory or async_session_factory

    if settings.use_celery_for_scans:
        try:
            from app.mobile.tasks.mobile_tasks import run_mobile_analysis_task

            async_result = run_mobile_analysis_task.delay(str(app_id))
            result = await db.execute(
                select(MobileApplication).where(MobileApplication.id == app_id)
            )
            app = result.scalar_one_or_none()
            if app is not None:
                app.celery_task_id = async_result.id
                await db.flush()
            logger.info("Mobile analysis %s queued on Celery task %s", app_id, async_result.id)
            return
        except Exception as exc:
            logger.warning("Celery mobile dispatch failed for %s", app_id)
            if settings.environment == "production":
                raise AppError(
                    "MOBILE_ANALYSIS_UNAVAILABLE",
                    "Mobile analysis is temporarily unavailable. Please retry the upload.",
                    status_code=503,
                ) from exc
            logger.info("Falling back to local background analysis for %s", app_id)

    async def _run() -> None:
        async with factory() as session:
            await MobileService(session).run_analysis(app_id)

    if background_tasks is not None:
        background_tasks.add_task(_run)
        logger.info("Mobile analysis %s queued on background task", app_id)
        return

    raise RuntimeError("No background task handler available for mobile dispatch")
