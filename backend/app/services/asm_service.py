"""Attack Surface Management service."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.asm.risk import compute_asset_risk_score
from app.asm.types import DiscoveredAsset
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.asm import AsmDiscoveryJob, Asset
from app.models.finding import Finding
from app.models.scan import ScanStatus
from app.models.user import User
from app.scanners.asm.discovery import discover_attack_surface
from app.scanners.passive_http import run_passive_http_scan
from app.schemas.asm import AsmDiscoverCreate, AttackSurfaceSummary
from app.services.audit_service import log_audit_event
from app.services.domain_service import DomainService
from app.services.finding_service import FindingService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

_ACTIVE_ASM_JOB_STATUSES = (ScanStatus.QUEUED, ScanStatus.RUNNING)


async def recover_stale_asm_jobs(db: AsyncSession) -> int:
    """Mark ASM discovery jobs stuck in active states as failed."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(minutes=settings.scan_stale_minutes)
    result = await db.execute(
        select(AsmDiscoveryJob).where(
            AsmDiscoveryJob.status.in_(_ACTIVE_ASM_JOB_STATUSES),
            func.coalesce(AsmDiscoveryJob.started_at, AsmDiscoveryJob.created_at) < cutoff,
        )
    )
    stale = list(result.scalars())
    for job in stale:
        job.status = ScanStatus.FAILED
        job.error_log = (
            f"Keşif {settings.scan_stale_minutes} dakikadan uzun süredir tamamlanmadı "
            "(zaman aşımı veya worker hatası)."
        )
        job.completed_at = datetime.now(UTC)
        logger.warning("Recovered stale ASM job %s (created %s)", job.id, job.created_at)
    if stale:
        await db.flush()
    return len(stale)


def build_asset_fingerprint(project_id: UUID, asset_type: str, identifier: str) -> str:
    payload = f"{project_id}:{asset_type}:{identifier.lower()}"
    return hashlib.sha256(payload.encode()).hexdigest()


class AsmService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_discovery(
        self,
        organization_id: UUID,
        project_id: UUID,
        data: AsmDiscoverCreate,
        *,
        actor: User,
    ) -> AsmDiscoveryJob:
        if not data.authorization_accepted:
            raise AppError(
                "AUTHORIZATION_REQUIRED",
                "You must confirm authorization to analyze this target.",
                status_code=400,
            )

        await ProjectService(self.db).get(organization_id, project_id)
        domain = await DomainService(self.db).get(organization_id, project_id, data.domain_id)
        settings = get_settings()

        if not settings.skip_domain_verification and not domain.is_verified:
            raise AppError(
                "DOMAIN_NOT_VERIFIED",
                "Domain must be verified before attack surface discovery.",
                status_code=400,
            )

        target = str(data.target_url)
        if not settings.skip_domain_verification and domain.hostname not in target:
            raise AppError(
                "TARGET_MISMATCH",
                f"Target must belong to verified domain {domain.hostname}.",
                status_code=400,
            )

        job = AsmDiscoveryJob(
            organization_id=organization_id,
            project_id=project_id,
            domain_id=domain.id,
            initiated_by=actor.id,
            target_url=target,
            status=ScanStatus.QUEUED,
        )
        self.db.add(job)
        await self.db.flush()

        await log_audit_event(
            self.db,
            action="asm.discovery.started",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="asm_discovery_job",
            resource_id=job.id,
            details={"target_url": target, "domain_id": str(domain.id)},
        )
        return job

    async def get_job(
        self, organization_id: UUID, project_id: UUID, job_id: UUID
    ) -> AsmDiscoveryJob:
        result = await self.db.execute(
            select(AsmDiscoveryJob).where(
                AsmDiscoveryJob.id == job_id,
                AsmDiscoveryJob.organization_id == organization_id,
                AsmDiscoveryJob.project_id == project_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise AppError("NOT_FOUND", "ASM discovery job not found.", status_code=404)
        return job

    async def list_jobs(
        self, organization_id: UUID, project_id: UUID, *, limit: int = 20
    ) -> list[AsmDiscoveryJob]:
        await ProjectService(self.db).get(organization_id, project_id)
        await recover_stale_asm_jobs(self.db)
        result = await self.db.execute(
            select(AsmDiscoveryJob)
            .where(
                AsmDiscoveryJob.organization_id == organization_id,
                AsmDiscoveryJob.project_id == project_id,
            )
            .order_by(AsmDiscoveryJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def list_assets(
        self,
        organization_id: UUID,
        project_id: UUID,
        *,
        domain_id: UUID | None = None,
        asset_type: str | None = None,
    ) -> list[Asset]:
        await ProjectService(self.db).get(organization_id, project_id)
        query = select(Asset).where(
            Asset.organization_id == organization_id,
            Asset.project_id == project_id,
        )
        if domain_id:
            query = query.where(Asset.domain_id == domain_id)
        if asset_type:
            query = query.where(Asset.asset_type == asset_type)
        query = query.order_by(Asset.risk_score.desc().nullslast(), Asset.identifier)
        result = await self.db.execute(query)
        return list(result.scalars())

    async def get_surface_summary(
        self, organization_id: UUID, project_id: UUID, *, domain_id: UUID | None = None
    ) -> AttackSurfaceSummary:
        assets = await self.list_assets(organization_id, project_id, domain_id=domain_id)
        jobs = await self.list_jobs(organization_id, project_id, limit=1)
        latest_job = jobs[0] if jobs else None

        technologies: dict[str, dict[str, str]] = {}
        cdn_waf: dict[str, dict[str, str]] = {}
        dns_records: dict[str, list[str]] = {}
        risk_scores: list[float] = []

        for asset in assets:
            if asset.risk_score is not None:
                risk_scores.append(asset.risk_score)
            meta = asset.metadata_ or {}
            if asset.asset_type == "domain" and meta.get("dns"):
                dns_records = meta["dns"]
            for tech in meta.get("technologies") or []:
                if isinstance(tech, dict):
                    key = f"{tech.get('category')}:{tech.get('name')}"
                    technologies[key] = tech
            for entry in meta.get("cdn_waf") or []:
                if isinstance(entry, dict):
                    cdn_waf[entry.get("name", "")] = entry

        return AttackSurfaceSummary(
            total_assets=len(assets),
            subdomains=sum(1 for a in assets if a.asset_type == "subdomain"),
            ip_addresses=sum(1 for a in assets if a.asset_type == "ip"),
            technologies=list(technologies.values()),
            cdn_waf=list(cdn_waf.values()),
            dns_records=dns_records,
            avg_risk_score=round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else None,
            max_risk_score=max(risk_scores) if risk_scores else None,
            last_discovery_at=latest_job.completed_at if latest_job else None,
            last_discovery_status=latest_job.status if latest_job else None,
        )

    async def _upsert_asset(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
        discovery_job_id: UUID,
        discovered: DiscoveredAsset,
        parent_map: dict[str, UUID],
        now: datetime,
    ) -> Asset:
        fingerprint = build_asset_fingerprint(project_id, discovered.asset_type, discovered.identifier)
        result = await self.db.execute(select(Asset).where(Asset.fingerprint == fingerprint))
        existing = result.scalar_one_or_none()

        parent_id = None
        if discovered.parent_identifier:
            parent_id = parent_map.get(discovered.parent_identifier)

        if existing:
            existing.status = discovered.status
            existing.metadata_ = discovered.metadata
            existing.exposure_score = discovered.exposure_score
            existing.url = discovered.url or existing.url
            existing.last_seen_at = now
            existing.last_scanned_at = now
            existing.discovery_job_id = discovery_job_id
            if parent_id:
                existing.parent_asset_id = parent_id
            asset = existing
        else:
            asset = Asset(
                organization_id=organization_id,
                project_id=project_id,
                domain_id=domain_id,
                discovery_job_id=discovery_job_id,
                parent_asset_id=parent_id,
                asset_type=discovered.asset_type,
                identifier=discovered.identifier,
                url=discovered.url,
                fingerprint=fingerprint,
                status=discovered.status,
                metadata_=discovered.metadata,
                exposure_score=discovered.exposure_score,
                first_seen_at=now,
                last_seen_at=now,
                last_scanned_at=now,
            )
            self.db.add(asset)
            await self.db.flush()

        parent_map[discovered.identifier] = asset.id
        return asset

    async def _update_asset_risk_scores(self, project_id: UUID) -> None:
        result = await self.db.execute(select(Asset).where(Asset.project_id == project_id))
        assets = list(result.scalars())
        for asset in assets:
            finding_stats = await self.db.execute(
                select(func.max(Finding.risk_score), func.count(Finding.id)).where(
                    Finding.asset_id == asset.id
                )
            )
            max_risk, count = finding_stats.one()
            asset.risk_score = compute_asset_risk_score(
                asset.metadata_,
                exposure_score=asset.exposure_score,
                max_finding_risk=max_risk,
                findings_count=count or 0,
            )

    def _build_job_summary(self, assets: list[Asset]) -> dict:
        techs: dict[str, dict] = {}
        cdn: list[dict] = []
        for asset in assets:
            meta = asset.metadata_ or {}
            for t in meta.get("technologies") or []:
                if isinstance(t, dict):
                    techs[f"{t.get('category')}:{t.get('name')}"] = t
            cdn.extend(meta.get("cdn_waf") or [])

        return {
            "total_assets": len(assets),
            "by_type": {
                t: sum(1 for a in assets if a.asset_type == t)
                for t in ("domain", "subdomain", "ip", "url", "api", "mobile")
            },
            "technologies": list(techs.values()),
            "cdn_waf": cdn,
            "avg_risk_score": round(
                sum(a.risk_score or 0 for a in assets) / len(assets), 1
            )
            if assets
            else None,
        }

    async def run_discovery_job(self, job_id: UUID) -> None:
        result = await self.db.execute(
            select(AsmDiscoveryJob).where(AsmDiscoveryJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            logger.error("ASM job %s not found", job_id)
            return

        if job.status in (ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED):
            return

        now = datetime.now(UTC)
        job.status = ScanStatus.RUNNING
        job.started_at = now
        await self.db.commit()

        try:
            settings = get_settings()
            discovered = await discover_attack_surface(
                job.target_url,
                max_subdomains=settings.asm_max_subdomains,
                max_hosts_probe=settings.asm_max_hosts_probe,
            )

            from app.models.scan import ScanJob

            asm_scan = ScanJob(
                organization_id=job.organization_id,
                project_id=job.project_id,
                domain_id=job.domain_id,
                initiated_by=job.initiated_by,
                scan_profile="asm",
                target_url=job.target_url,
                status=ScanStatus.PARSING,
                scope_config={"asm_discovery_job_id": str(job.id)},
            )
            self.db.add(asm_scan)
            await self.db.flush()

            parent_map: dict[str, UUID] = {}
            saved_assets: list[Asset] = []
            url_to_asset: dict[str, Asset] = {}

            for item in discovered:
                asset = await self._upsert_asset(
                    organization_id=job.organization_id,
                    project_id=job.project_id,
                    domain_id=job.domain_id,
                    discovery_job_id=job.id,
                    discovered=item,
                    parent_map=parent_map,
                    now=now,
                )
                saved_assets.append(asset)
                if item.url:
                    url_to_asset[item.url.rstrip("/")] = asset

            finding_service = FindingService(self.db)
            probe_urls = [
                a.url.rstrip("/")
                for a in saved_assets
                if a.url and a.asset_type in ("domain", "subdomain") and a.status != "inactive"
            ][: settings.asm_max_hosts_probe]

            for url in probe_urls:
                raw_findings = await run_passive_http_scan(url)
                asset = url_to_asset.get(url)
                await finding_service.persist_scan_findings(
                    organization_id=job.organization_id,
                    project_id=job.project_id,
                    scan_job_id=asm_scan.id,
                    raw_findings=raw_findings,
                    target_url=url,
                    asset_id=asset.id if asset else None,
                )

            asm_scan.status = ScanStatus.COMPLETED
            asm_scan.findings_count = 0
            await self._update_asset_risk_scores(job.project_id)

            job.status = ScanStatus.COMPLETED
            job.assets_count = len(saved_assets)
            job.summary = self._build_job_summary(saved_assets)
            job.completed_at = datetime.now(UTC)
            await self.db.commit()
            logger.info("ASM job %s completed with %s assets", job_id, len(saved_assets))
        except Exception as exc:
            logger.exception("ASM job %s failed", job_id)
            await self.db.rollback()
            result = await self.db.execute(
                select(AsmDiscoveryJob).where(AsmDiscoveryJob.id == job_id)
            )
            job = result.scalar_one()
            job.status = ScanStatus.FAILED
            job.error_log = str(exc)
            job.completed_at = datetime.now(UTC)
            await self.db.commit()
