"""Scan job orchestration."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.scan import AuthorizationAcceptance, ScanJob, ScanProfile, ScanStatus
from app.models.user import User
from app.scanners.orchestrator import run_scan_for_profile
from app.schemas.scan import ScanCreate
from app.services.audit_service import log_audit_event
from app.services.domain_service import DomainService
from app.services.finding_service import FindingService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

_ACTIVE_SCAN_STATUSES = (
    ScanStatus.QUEUED,
    ScanStatus.VALIDATING,
    ScanStatus.RUNNING,
    ScanStatus.PARSING,
)

class ScanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_profiles(self) -> list[ScanProfile]:
        result = await self.db.execute(
            select(ScanProfile).where(ScanProfile.is_active.is_(True)).order_by(ScanProfile.name)
        )
        return list(result.scalars())

    async def get_profile(self, name: str) -> ScanProfile:
        result = await self.db.execute(
            select(ScanProfile).where(ScanProfile.name == name, ScanProfile.is_active.is_(True))
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise AppError("NOT_FOUND", "Scan profile not found.", status_code=404)
        return profile

    async def create(
        self,
        organization_id: UUID,
        data: ScanCreate,
        *,
        actor: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ScanJob:
        if not data.authorization_accepted:
            raise AppError(
                "AUTHORIZATION_REQUIRED",
                "You must confirm authorization to scan this target.",
                status_code=400,
            )

        await ProjectService(self.db).get(organization_id, data.project_id)
        domain = await DomainService(self.db).get(organization_id, data.project_id, data.domain_id)
        settings = get_settings()

        if not settings.skip_domain_verification and not domain.is_verified:
            raise AppError(
                "DOMAIN_NOT_VERIFIED",
                "Domain must be verified before scanning.",
                status_code=400,
            )

        profile = await self.get_profile(data.scan_profile)
        target = str(data.target_url)
        if not settings.skip_domain_verification and domain.hostname not in target:
            raise AppError(
                "TARGET_MISMATCH",
                f"Target URL must belong to verified domain {domain.hostname}.",
                status_code=400,
            )

        if (
            profile.name in ("deep", "code")
            and domain.hostname
            and not settings.skip_domain_verification
        ):
            project = await ProjectService(self.db).get(organization_id, data.project_id)
            if project.environment == "production":
                raise AppError(
                    "PROFILE_NOT_ALLOWED",
                    "Deep/Code scans are not allowed on production projects.",
                    status_code=400,
                )

        scan = ScanJob(
            organization_id=organization_id,
            project_id=data.project_id,
            domain_id=data.domain_id,
            initiated_by=actor.id,
            scan_profile=profile.name,
            target_url=target,
            status=ScanStatus.QUEUED,
            scope_config=data.scope_config,
        )
        self.db.add(scan)
        await self.db.flush()

        self.db.add(
            AuthorizationAcceptance(
                user_id=actor.id,
                organization_id=organization_id,
                scan_job_id=scan.id,
                target=target,
                scan_profile=profile.name,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

        await log_audit_event(
            self.db,
            action="scan.started",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="scan_job",
            resource_id=scan.id,
            ip_address=ip_address,
            details={"target": target, "profile": profile.name},
        )
        await self.db.flush()
        return scan

    async def list_for_org(self, organization_id: UUID) -> list[ScanJob]:
        result = await self.db.execute(
            select(ScanJob)
            .where(ScanJob.organization_id == organization_id)
            .order_by(ScanJob.created_at.desc())
            .limit(100)
        )
        return list(result.scalars())

    async def get(self, organization_id: UUID, scan_id: UUID) -> ScanJob:
        result = await self.db.execute(
            select(ScanJob).where(
                ScanJob.id == scan_id,
                ScanJob.organization_id == organization_id,
            )
        )
        scan = result.scalar_one_or_none()
        if scan is None:
            raise AppError("NOT_FOUND", "Scan not found.", status_code=404)
        return scan

    async def cancel(self, organization_id: UUID, scan_id: UUID, *, actor: User) -> ScanJob:
        scan = await self.get(organization_id, scan_id)
        if scan.status in (ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED):
            raise AppError("INVALID_STATE", "Scan cannot be cancelled.", status_code=400)
        scan.status = ScanStatus.CANCELLED
        scan.cancelled_at = datetime.now(UTC)
        await self.db.flush()
        return scan


async def recover_stale_scan_jobs(db: AsyncSession) -> int:
    """Mark scans stuck in active states as failed (worker crash / hang recovery)."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(minutes=settings.scan_stale_minutes)
    result = await db.execute(
        select(ScanJob).where(
            ScanJob.status.in_(_ACTIVE_SCAN_STATUSES),
            func.coalesce(ScanJob.started_at, ScanJob.created_at) < cutoff,
        )
    )
    stale = list(result.scalars())
    for scan in stale:
        scan.status = ScanStatus.FAILED
        scan.error_log = (
            f"Tarama {settings.scan_stale_minutes} dakikadan uzun süredir tamamlanmadı "
            "(zaman aşımı veya worker hatası)."
        )
        scan.completed_at = datetime.now(UTC)
        logger.warning("Recovered stale scan %s (created %s)", scan.id, scan.created_at)
    if stale:
        await db.flush()
    return len(stale)


async def fail_scan_job_by_id(
    scan_id: UUID | str,
    error: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Mark a scan failed using a fresh session (safe after Celery kill / rollback)."""
    scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
    async with session_factory() as db:
        result = await db.execute(select(ScanJob).where(ScanJob.id == scan_uuid))
        scan = result.scalar_one_or_none()
        if scan is None or scan.status in (
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
            ScanStatus.CANCELLED,
        ):
            return
        await _mark_scan_failed(db, scan, error)


async def _mark_scan_failed(
    db: AsyncSession,
    scan: ScanJob,
    error: str,
) -> None:
    scan.status = ScanStatus.FAILED
    scan.error_log = error[:4000]
    scan.completed_at = datetime.now(UTC)
    await db.commit()


async def run_scan_job(
    scan_id: UUID | str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Execute scan tools and persist normalized findings (Phase 5)."""
    scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
    await asyncio.sleep(0.5)
    async with session_factory() as db:
        scan: ScanJob | None = None
        try:
            result = await db.execute(select(ScanJob).where(ScanJob.id == scan_uuid))
            scan = result.scalar_one_or_none()
            if scan is None or scan.status == ScanStatus.CANCELLED:
                return
            if scan.status == ScanStatus.FAILED:
                return
            if scan.status != ScanStatus.QUEUED:
                logger.info("Scan %s already active (%s), skipping duplicate run", scan_uuid, scan.status)
                return

            claimed = await db.execute(
                update(ScanJob)
                .where(
                    ScanJob.id == scan_uuid,
                    ScanJob.status == ScanStatus.QUEUED,
                )
                .values(
                    status=ScanStatus.VALIDATING,
                    started_at=datetime.now(UTC),
                )
            )
            await db.commit()
            if claimed.rowcount == 0:
                logger.info("Scan %s claim lost (already started elsewhere)", scan_uuid)
                return

            result = await db.execute(select(ScanJob).where(ScanJob.id == scan_uuid))
            scan = result.scalar_one_or_none()
            if scan is None:
                return

            scan.status = ScanStatus.RUNNING
            await db.commit()

            try:
                raw_findings = await run_scan_for_profile(scan.target_url, scan.scan_profile)
            except Exception as exc:
                await _mark_scan_failed(db, scan, str(exc))
                return

            scan.status = ScanStatus.PARSING
            await db.commit()

            finding_service = FindingService(db)
            saved = await finding_service.persist_scan_findings(
                organization_id=scan.organization_id,
                project_id=scan.project_id,
                scan_job_id=scan.id,
                raw_findings=raw_findings,
                target_url=scan.target_url,
            )

            scan.status = ScanStatus.COMPLETED
            scan.findings_count = len(saved)
            scan.completed_at = datetime.now(UTC)
            await db.commit()

            from app.services.site_profile_service import SiteProfileService

            await SiteProfileService(db).collect_for_scan(scan)
            await db.commit()

            # A benchmark run must be explicitly linked to this hidden system-scope scan.
            from app.services.benchmark_run_service import BenchmarkRunService

            await BenchmarkRunService(db).complete_for_scan(scan)
            await db.commit()

            from app.services.monitoring_service import MonitoringService

            await MonitoringService.after_scan_completed(db, scan)
            await db.commit()

            from app.services.ai_dispatch import dispatch_ai_enrichment

            await dispatch_ai_enrichment(scan.id)
            logger.info("Scan %s completed with %s findings", scan_uuid, len(saved))
        except Exception as exc:
            logger.exception("Scan job %s failed", scan_uuid)
            await db.rollback()
            await fail_scan_job_by_id(scan_uuid, str(exc), session_factory)
