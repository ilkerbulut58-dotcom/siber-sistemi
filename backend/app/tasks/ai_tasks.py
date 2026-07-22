"""Celery tasks for LLM finding enrichment."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.finding import Finding
from app.services.ai_analysis_service import enrich_findings_with_llm
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _enrich_scan_findings(scan_id: UUID) -> dict[str, int | str]:
    async with async_session_factory() as db:
        result = await db.execute(
            select(Finding).where(Finding.scan_job_id == scan_id).order_by(Finding.risk_score.desc())
        )
        findings = list(result.scalars())
        if not findings:
            return {"scan_id": str(scan_id), "total": 0, "enriched": 0, "skipped": 0}

        stats = await enrich_findings_with_llm(findings)
        await db.commit()
        logger.info("LLM enrichment for scan %s: %s", scan_id, stats)
        return {"scan_id": str(scan_id), **stats}


@celery_app.task(name="siber.enrich_scan_findings", bind=True, max_retries=1)
def enrich_scan_findings_task(self, scan_id: str) -> dict[str, int | str]:
    """Enrich all findings for a completed scan with LLM analysis."""
    logger.info("Celery AI enrichment starting for scan %s", scan_id)
    return asyncio.run(_enrich_scan_findings(UUID(scan_id)))
