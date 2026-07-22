"""Celery tasks for scheduled monitoring scans."""

from __future__ import annotations

import asyncio
import logging

from app.core.database import async_session_factory
from app.services.monitoring_service import MonitoringService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="siber.check_scheduled_scans")
def check_scheduled_scans_task() -> dict[str, int]:
    return asyncio.run(_check_scheduled_scans())


@celery_app.task(name="siber.recover_stale_scans")
def recover_stale_scans_task() -> dict[str, int]:
    return asyncio.run(_recover_stale_scans())


async def _recover_stale_scans() -> dict[str, int]:
    async with async_session_factory() as db:
        from app.services.asm_service import recover_stale_asm_jobs
        from app.services.scan_service import recover_stale_scan_jobs

        recovered_scans = await recover_stale_scan_jobs(db)
        recovered_asm = await recover_stale_asm_jobs(db)
        await db.commit()
    if recovered_scans:
        logger.warning("Recovered %s stale scan job(s)", recovered_scans)
    if recovered_asm:
        logger.warning("Recovered %s stale ASM job(s)", recovered_asm)
    return {"recovered_scans": recovered_scans, "recovered_asm": recovered_asm}


async def _check_scheduled_scans() -> dict[str, int]:
    triggered = 0
    async with async_session_factory() as db:
        from app.services.asm_service import recover_stale_asm_jobs
        from app.services.scan_service import recover_stale_scan_jobs

        recovered_scans = await recover_stale_scan_jobs(db)
        recovered_asm = await recover_stale_asm_jobs(db)
        service = MonitoringService(db)
        due = await service.due_schedules()
        for schedule in due:
            try:
                scan = await service.trigger_schedule(schedule)
                await db.flush()
                from app.services.scan_service import run_scan_job

                await run_scan_job(scan.id, async_session_factory)
                triggered += 1
            except Exception:
                logger.exception("Failed to trigger schedule %s", schedule.id)
        await db.commit()
    logger.info(
        "Scheduled scan check complete: %s triggered, %s stale scans recovered, %s stale ASM jobs recovered",
        triggered,
        recovered_scans,
        recovered_asm,
    )
    return {
        "triggered": triggered,
        "recovered_scans": recovered_scans,
        "recovered_asm": recovered_asm,
    }
