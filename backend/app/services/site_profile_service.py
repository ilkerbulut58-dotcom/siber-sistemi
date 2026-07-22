"""Persist and serve target site intelligence profiles."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.scan import ScanJob
from app.models.site_profile import TargetSiteProfile
from app.scanners.site_intelligence import collect_site_intelligence
from app.schemas.site_profile import SensitiveDataSummary, SiteProfileResponse

logger = logging.getLogger(__name__)

SENSITIVE_RULE_PREFIX = "sensitive-"
PASSWORD_RULES = {"sensitive-hardcoded-password", "sensitive-db-connection-string", "sensitive-api-secret-assignment"}
BANK_RULES = {"sensitive-turkish-iban", "sensitive-generic-iban", "sensitive-bank-account-hint"}
PAYMENT_RULES = {"sensitive-credit-card-number"}


class SiteProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def collect_for_scan(self, scan: ScanJob) -> TargetSiteProfile | None:
        try:
            profile_data = await collect_site_intelligence(scan.target_url)
        except Exception as exc:
            logger.exception("Site intelligence collection failed for scan %s", scan.id)
            profile_data = {
                "target_url": scan.target_url,
                "hostname": scan.target_url,
                "error": str(exc),
            }

        sensitive = await self._sensitive_summary(scan.id)
        profile_data["sensitive_data"] = sensitive.model_dump()

        existing = await self.db.execute(
            select(TargetSiteProfile).where(TargetSiteProfile.scan_job_id == scan.id)
        )
        row = existing.scalar_one_or_none()
        hostname = profile_data.get("hostname") or scan.target_url

        if row:
            row.profile = profile_data
            row.target_url = scan.target_url
            row.hostname = str(hostname)
        else:
            row = TargetSiteProfile(
                organization_id=scan.organization_id,
                project_id=scan.project_id,
                scan_job_id=scan.id,
                target_url=scan.target_url,
                hostname=str(hostname),
                profile=profile_data,
            )
            self.db.add(row)

        await self.db.flush()
        return row

    async def get_for_scan(self, organization_id: UUID, scan_id: UUID) -> SiteProfileResponse | None:
        result = await self.db.execute(
            select(TargetSiteProfile).where(
                TargetSiteProfile.organization_id == organization_id,
                TargetSiteProfile.scan_job_id == scan_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        sensitive = await self._sensitive_summary(scan_id)
        return SiteProfileResponse(
            id=row.id,
            organization_id=row.organization_id,
            project_id=row.project_id,
            scan_job_id=row.scan_job_id,
            target_url=row.target_url,
            hostname=row.hostname,
            profile=row.profile,
            sensitive_data=sensitive,
            collected_at=row.collected_at,
        )

    async def _sensitive_summary(self, scan_id: UUID) -> SensitiveDataSummary:
        result = await self.db.execute(
            select(Finding.source_rule_id).where(
                Finding.scan_job_id == scan_id,
                Finding.source_tool == "sensitive_data",
            )
        )
        rule_ids = [row[0] for row in result.all() if row[0]]

        password = sum(1 for r in rule_ids if r in PASSWORD_RULES)
        bank = sum(1 for r in rule_ids if r in BANK_RULES)
        payment = sum(1 for r in rule_ids if r in PAYMENT_RULES)
        other = sum(
            1
            for r in rule_ids
            if r and r.startswith(SENSITIVE_RULE_PREFIX) and r not in PASSWORD_RULES | BANK_RULES | PAYMENT_RULES
        )

        return SensitiveDataSummary(
            password_findings=password,
            bank_findings=bank,
            payment_findings=payment,
            other_secrets=other,
        )
