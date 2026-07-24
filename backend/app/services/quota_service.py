"""Scan access policy — platform admins get unrestricted scans; others follow pilot/subscription rules."""

from __future__ import annotations

from app.core.config import Settings
from app.models.organization import Organization
from app.models.user import User
from app.services.pilot_service import PilotService


class QuotaService:
    @staticmethod
    def is_unrestricted_scan_actor(actor: User) -> bool:
        return actor.is_platform_admin

    @staticmethod
    def requires_domain_verification(actor: User, settings: Settings) -> bool:
        if actor.is_platform_admin:
            return False
        return not settings.skip_domain_verification

    @staticmethod
    def should_enforce_scan_limits(
        actor: User,
        organization: Organization,
        settings: Settings,
    ) -> bool:
        if actor.is_platform_admin:
            return False
        return settings.environment in {"production", "staging"} or organization.is_pilot

    @staticmethod
    def effective_daily_quota(
        actor: User,
        organization: Organization,
        default_quota: int,
    ) -> int | None:
        """Return daily scan limit, or None when unlimited (platform admin)."""
        if actor.is_platform_admin:
            return None
        return PilotService.effective_daily_quota(organization, default_quota)