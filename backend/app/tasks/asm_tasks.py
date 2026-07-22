"""Celery tasks for ASM discovery."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.core.database import async_session_factory
from app.services.asm_service import AsmService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="siber.run_asm_discovery", bind=True, max_retries=0)
def run_asm_discovery_task(self, job_id: str) -> dict[str, str]:
    logger.info("Celery worker starting ASM discovery %s", job_id)

    async def _run() -> None:
        async with async_session_factory() as db:
            await AsmService(db).run_discovery_job(UUID(job_id))

    asyncio.run(_run())
    return {"job_id": job_id, "status": "finished"}
