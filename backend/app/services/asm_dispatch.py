"""Dispatch ASM discovery jobs to Celery or inline execution."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.asm import AsmDiscoveryJob
from app.services.asm_service import AsmService

logger = logging.getLogger(__name__)


async def dispatch_asm_discovery(
    job_id: UUID,
    *,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
    session_factory: async_sessionmaker | None = None,
) -> None:
    settings = get_settings()
    factory = session_factory or async_session_factory

    if settings.use_celery_for_scans:
        try:
            from app.tasks.asm_tasks import run_asm_discovery_task

            async_result = run_asm_discovery_task.delay(str(job_id))
            result = await db.execute(
                select(AsmDiscoveryJob).where(AsmDiscoveryJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job is not None:
                job.celery_task_id = async_result.id
                await db.flush()
            logger.info("ASM job %s queued on Celery task %s", job_id, async_result.id)
            return
        except Exception as exc:
            logger.warning("Celery ASM dispatch failed for %s, falling back: %s", job_id, exc)

    async def _run() -> None:
        async with factory() as session:
            await AsmService(session).run_discovery_job(job_id)

    if background_tasks is not None:
        background_tasks.add_task(_run)
        logger.info("ASM job %s queued on background task", job_id)
        return

    raise RuntimeError("No background task handler available for ASM dispatch")
