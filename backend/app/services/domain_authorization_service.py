"""Domain verification expiry, revoke, and scan authorization gates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.domain import Domain
from app.models.organization import Organization


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def verification_expires_at(domain: Domain) -> datetime | None:
    verified_at = _utc(domain.verified_at)
    if verified_at is None:
        return None
    ttl_days = get_settings().domain_verification_ttl_days
    if domain.verification_method == "manual_admin":
        ttl_days = get_settings().domain_manual_verification_ttl_days
    return verified_at + timedelta(days=ttl_days)


def verification_status(domain: Domain) -> str:
    if domain.revoked_at is not None:
        return "revoked"
    if not domain.is_verified:
        return "unverified"
    expires = verification_expires_at(domain)
    if expires is not None and _utc(datetime.now(UTC)) > expires:
        return "expired"
    return "verified"


def is_verification_valid(domain: Domain) -> bool:
    return verification_status(domain) == "verified"


def assert_domain_scan_allowed(
    domain: Domain,
    organization: Organization,
    profile_name: str,
) -> None:
    """Gate scans on verification validity, revoke, pilot state, and profile."""
    from app.services.pilot_service import PilotService

    PilotService.assert_can_scan(organization)

    status = verification_status(domain)
    active_profiles = {"deep", "code"}

    if status == "revoked":
        raise AppError(
            "DOMAIN_REVOKED",
            "Domain verification has been revoked.",
            status_code=403,
        )

    if status in {"unverified", "expired"}:
        if profile_name in active_profiles or profile_name.endswith("-active"):
            raise AppError(
                "DOMAIN_VERIFICATION_EXPIRED" if status == "expired" else "DOMAIN_NOT_VERIFIED",
                "Domain must be verified and within the verification validity window before active scanning.",
                status_code=403,
            )
        raise AppError(
            "DOMAIN_VERIFICATION_EXPIRED" if status == "expired" else "DOMAIN_NOT_VERIFIED",
            "Domain must be verified before scanning.",
            status_code=400,
        )

    if profile_name in active_profiles and not domain.active_scan_allowed:
        raise AppError(
            "ACTIVE_SCAN_NOT_ALLOWED",
            "Active scanning requires domain admin approval.",
            status_code=403,
        )
