"""Dispatch scan jobs to Celery or FastAPI background tasks."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.scan import ScanJob
from app.services.scan_service import run_scan_job

logger = logging.getLogger(__name__)


async def dispatch_scan_job(
    scan_id: UUID,
    *,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
    session_factory: async_sessionmaker | None = None,
) -> None:
    """Queue scan execution.

    Prefer FastAPI BackgroundTasks when available — production Celery workers can
    accept tasks without executing them if misconfigured, leaving scans stuck
    in ``queued`` forever.
    """
    settings = get_settings()
    factory = session_factory or async_session_factory

    if background_tasks is not None:
        background_tasks.add_task(run_scan_job, scan_id, factory)
        logger.info("Scan %s queued on FastAPI background task", scan_id)
        return

    if settings.use_celery_for_scans:
        try:
            from app.tasks.scan_tasks import run_scan_job_task

            async_result = run_scan_job_task.delay(str(scan_id))
            result = await db.execute(select(ScanJob).where(ScanJob.id == scan_id))
            scan = result.scalar_one_or_none()
            if scan is not None:
                scan.celery_task_id = async_result.id
                await db.flush()
            logger.info("Scan %s queued on Celery task %s", scan_id, async_result.id)
            return
        except Exception as exc:
            logger.warning("Celery dispatch failed for %s: %s", scan_id, exc)

    raise RuntimeError("No background task handler available for scan dispatch")
