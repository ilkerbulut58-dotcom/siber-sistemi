"""Controlled closed pilot tenant guards."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.organization import Organization
from app.models.scan import ScanJob, ScanStatus


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _next_quota_reset() -> datetime:
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return tomorrow


class PilotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def is_expert_tenant(organization: Organization) -> bool:
        return organization.tenant_type == "expert_security_test"

    @staticmethod
    def show_onboarding_checklist(organization: Organization) -> bool:
        return organization.is_pilot or PilotService.is_expert_tenant(organization)

    @staticmethod
    def assert_can_scan(organization: Organization) -> None:
        if not organization.is_pilot and not PilotService.is_expert_tenant(organization):
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
        pilot_starts_at = _as_utc(organization.pilot_starts_at)
        pilot_ends_at = _as_utc(organization.pilot_ends_at)
        if pilot_starts_at and now < pilot_starts_at:
            raise AppError(
                "PILOT_NOT_STARTED",
                "Pilot access has not started yet.",
                status_code=403,
            )
        if pilot_ends_at and now > pilot_ends_at:
            raise AppError(
                "PILOT_EXPIRED",
                "Pilot access has expired.",
                status_code=403,
            )

    @staticmethod
    def effective_daily_quota(organization: Organization, default_quota: int) -> int:
        if organization.tenant_type == "expert_security_test" and organization.expert_test_quota is not None:
            return organization.expert_test_quota
        if organization.is_pilot and organization.pilot_scan_quota is not None:
            return organization.pilot_scan_quota
        return default_quota

    @staticmethod
    def assert_active_scan_allowed(organization: Organization, profile_name: str) -> None:
        active_profiles = {"deep", "code"}
        if (
            (organization.is_pilot or PilotService.is_expert_tenant(organization))
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
        domain_count: int,
        verified_domain_count: int,
        authorization_accepted: bool,
        completed_scan_count: int = 0,
        feedback_count: int = 0,
        first_project_id: UUID | None = None,
        pending_domain_id: UUID | None = None,
        latest_completed_scan_id: UUID | None = None,
        scan_concurrency_limit: int = 1,
    ) -> dict:
        expert = self.is_expert_tenant(organization)
        show_checklist = self.show_onboarding_checklist(organization)

        if expert:
            steps = [
                {
                    "step_id": "domain_added",
                    "label": "Add domain",
                    "completed": domain_count > 0,
                },
                {
                    "step_id": "domain_verified",
                    "label": "Verify domain ownership",
                    "completed": verified_domain_count > 0,
                },
                {
                    "step_id": "safe_scan_started",
                    "label": "Start safe scan",
                    "completed": completed_scan_count > 0,
                },
                {
                    "step_id": "findings_reviewed",
                    "label": "Review findings and report",
                    "completed": completed_scan_count > 0,
                },
                {
                    "step_id": "feedback_or_retest",
                    "label": "Send feedback or retest",
                    "completed": feedback_count > 0,
                },
            ]
            ready = verified_domain_count > 0 and authorization_accepted
        else:
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
                    "completed": domain_count > 0,
                },
                {
                    "step_id": "domain_verified",
                    "label": "Verify domain ownership",
                    "completed": verified_domain_count > 0,
                },
                {
                    "step_id": "authorization_accepted",
                    "label": "Accept scan authorization",
                    "completed": authorization_accepted,
                },
            ]
            ready = all(step["completed"] for step in steps)

        return {
            "organization_id": organization.id,
            "is_pilot": organization.is_pilot,
            "steps": steps,
            "ready_to_scan": ready,
            "pilot_ends_at": organization.pilot_ends_at,
            "pilot_active_scan_allowed": organization.pilot_active_scan_allowed,
            "show_onboarding_checklist": show_checklist,
            "tenant_type": organization.tenant_type,
            "scan_concurrency_limit": scan_concurrency_limit,
            "quota_resets_at": _next_quota_reset(),
            "first_project_id": first_project_id,
            "pending_domain_id": pending_domain_id,
            "latest_completed_scan_id": latest_completed_scan_id,
        }
