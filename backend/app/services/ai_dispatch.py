"""Dispatch AI enrichment after scan completion."""

from __future__ import annotations

import logging
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def dispatch_ai_enrichment(scan_id: UUID) -> None:
    """Queue or run LLM enrichment; never raises — scan completion must not depend on AI."""
    settings = get_settings()
    if not settings.ai_enabled:
        return

    if not settings.openai_api_key.strip():
        logger.info("AI enabled but no API key — skipping enrichment for scan %s", scan_id)
        return

    if settings.use_celery_for_scans:
        try:
            from app.tasks.ai_tasks import enrich_scan_findings_task

            enrich_scan_findings_task.delay(str(scan_id))
            logger.info("AI enrichment queued on Celery for scan %s", scan_id)
            return
        except Exception as exc:
            logger.warning("Celery AI dispatch failed for %s, running inline: %s", scan_id, exc)

    await _run_inline_enrichment(scan_id)


async def _run_inline_enrichment(scan_id: UUID) -> None:
    from app.tasks.ai_tasks import _enrich_scan_findings

    try:
        await _enrich_scan_findings(scan_id)
    except Exception:
        logger.exception("Inline AI enrichment failed for scan %s", scan_id)
