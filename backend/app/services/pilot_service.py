"""Controlled closed pilot tenant guards."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.organization import Organization
from app.models.scan import ScanJob


class PilotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def assert_can_scan(organization: Organization) -> None:
        if not organization.is_pilot:
            return
        if not organization.is_active:
            raise AppError(
                "PILOT_SUSPENDED",
                "Pilot account is inactive.",
                status_code=403,
            )
        if organization.scans_disabled:
            raise AppError(
                "PILOT_SCANS_DISABLED",
                "Scanning is temporarily disabled for this pilot account.",
                status_code=403,
            )
        now = datetime.now(UTC)
        if organization.pilot_starts_at and now < organization.pilot_starts_at:
            raise AppError(
                "PILOT_NOT_STARTED",
                "Pilot access has not started yet.",
                status_code=403,
            )
        if organization.pilot_ends_at and now > organization.pilot_ends_at:
            raise AppError(
                "PILOT_EXPIRED",
                "Pilot access has expired.",
                status_code=403,
            )

    @staticmethod
    def effective_daily_quota(organization: Organization, default_quota: int) -> int:
        if organization.is_pilot and organization.pilot_scan_quota is not None:
            return organization.pilot_scan_quota
        return default_quota

    @staticmethod
    def assert_active_scan_allowed(organization: Organization, profile_name: str) -> None:
        active_profiles = {"deep", "code"}
        if (
            organization.is_pilot
            and profile_name in active_profiles
            and not organization.pilot_active_scan_allowed
        ):
            raise AppError(
                "PILOT_ACTIVE_SCAN_DISABLED",
                "Active scanning is not enabled for this pilot account.",
                status_code=403,
            )

    async def daily_scan_count(self, organization_id: UUID) -> int:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count())
            .select_from(ScanJob)
            .where(
                ScanJob.organization_id == organization_id,
                ScanJob.created_at >= today_start,
            )
        )
        return int(result.scalar_one())

    async def get_onboarding_status(
        self,
        organization: Organization,
        *,
        owner_email_verified: bool,
        verified_domain_count: int,
        authorization_accepted: bool,
    ) -> dict:
        steps = [
            {"step_id": "account_created", "label": "Create account", "completed": True},
            {
                "step_id": "email_verified",
                "label": "Verify email",
                "completed": owner_email_verified,
            },
            {
                "step_id": "domain_added",
                "label": "Add domain",
                "completed": verified_domain_count > 0 or not organization.is_pilot,
            },
            {
                "step_id": "domain_verified",
                "label": "Verify domain ownership",
                "completed": verified_domain_count > 0,
            },
            {
                "step_id": "authorization_accepted",
                "label": "Accept scan authorization",
                "completed": authorization_accepted or not organization.is_pilot,
            },
        ]
        ready = all(step["completed"] for step in steps)
        return {
            "organization_id": organization.id,
            "is_pilot": organization.is_pilot,
            "steps": steps,
            "ready_to_scan": ready,
        }
