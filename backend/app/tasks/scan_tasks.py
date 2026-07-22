"""Celery tasks for scan execution."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded

from app.core.database import async_session_factory
from app.services.scan_service import fail_scan_job_by_id, run_scan_job
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_SCAN_TIMEOUT_MESSAGE = (
    "Tarama worker zaman aşımına uğradı (10 dakika). "
    "Lütfen Güvenli profil ile tekrar deneyin veya destek ile iletişime geçin."
)


@celery_app.task(name="siber.run_scan_job", bind=True, max_retries=0)
def run_scan_job_task(self, scan_id: str) -> dict[str, str]:
    """Run async scan job inside Celery worker process."""
    logger.info("Celery worker starting scan %s (task %s)", scan_id, self.request.id)
    try:
        asyncio.run(run_scan_job(UUID(scan_id), async_session_factory))
        return {"scan_id": scan_id, "status": "finished"}
    except (SoftTimeLimitExceeded, TimeLimitExceeded) as exc:
        logger.error("Scan %s hit Celery time limit: %s", scan_id, exc)
        asyncio.run(
            fail_scan_job_by_id(UUID(scan_id), _SCAN_TIMEOUT_MESSAGE, async_session_factory)
        )
        return {"scan_id": scan_id, "status": "failed", "error": "timeout"}
    except Exception as exc:
        logger.exception("Scan %s Celery task failed", scan_id)
        try:
            asyncio.run(fail_scan_job_by_id(UUID(scan_id), str(exc), async_session_factory))
        except Exception:
            logger.exception("Could not mark scan %s as failed after task error", scan_id)
        raise
