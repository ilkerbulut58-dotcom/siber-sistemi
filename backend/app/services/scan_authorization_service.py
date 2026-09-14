"""Central scan target authorization (DNS, admin assignment, admin DNS exempt)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.domain import Domain
from app.models.mixins import OrganizationRole
from app.models.organization import Organization, OrganizationMember
from app.models.scan_target import PredefinedScanTarget, ScanTargetAssignment
from app.models.user import User
from app.services.domain_authorization_service import verification_status
from app.services.domain_verification_service import normalize_hostname
from app.services.pilot_service import PilotService

DNS_VERIFICATION_METHODS = frozenset({"dns_txt", "well_known_file", "meta_tag"})
AUTHORIZATION_DNS = "dns_verification"
AUTHORIZATION_ADMIN_ASSIGNMENT = "admin_test_assignment"
AUTHORIZATION_ADMIN_DNS_EXEMPT = "admin_dns_exempt"
AUTHORIZATION_DEV_SKIP = "dev_skip"
AUTHORIZATION_PLATFORM = "platform_manual"


@dataclass(frozen=True)
class ScanAuthorization:
    source: str
    hostname: str
    detail: dict | None = None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ScanAuthorizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def active_assignment(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        hostname: str,
        profile_name: str | None = None,
    ) -> ScanTargetAssignment | None:
        host = normalize_hostname(hostname)
        now = _utc_now()
        result = await self.db.execute(
            select(ScanTargetAssignment, PredefinedScanTarget)
            .join(PredefinedScanTarget, PredefinedScanTarget.id == ScanTargetAssignment.predefined_target_id)
            .where(
                ScanTargetAssignment.user_id == user_id,
                ScanTargetAssignment.organization_id == organization_id,
                ScanTargetAssignment.revoked_at.is_(None),
                PredefinedScanTarget.is_active.is_(True),
                PredefinedScanTarget.hostname == host,
            )
        )
        for assignment, target in result.all():
            starts = _utc(assignment.starts_at)
            ends = _utc(assignment.ends_at)
            if starts and now < starts:
                continue
            if ends and now > ends:
                continue
            if profile_name is not None:
                allowed = assignment.allowed_profiles or [target.default_scan_profile]
                if allowed and profile_name not in allowed:
                    raise AppError(
                        "SCAN_PROFILE_NOT_ALLOWED",
                        "This test target assignment does not allow the selected scan profile.",
                        status_code=403,
                    )
            return assignment
        return None

    async def user_is_org_admin(self, user_id: UUID, organization_id: UUID) -> bool:
        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.organization_id == organization_id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            return False
        return membership.role in (OrganizationRole.ADMIN.value, OrganizationRole.OWNER.value)

    async def resolve_scan_authorization(
        self,
        *,
        actor: User,
        organization: Organization,
        domain: Domain,
        profile_name: str,
    ) -> ScanAuthorization:
        hostname = normalize_hostname(domain.hostname)
        if domain.hostname != hostname:
            raise AppError(
                "INVALID_HOSTNAME",
                "Domain hostname normalization mismatch.",
                status_code=400,
            )

        if not self.settings.domain_verification_enforced():
            return ScanAuthorization(source=AUTHORIZATION_DEV_SKIP, hostname=hostname)

        PilotService.assert_can_scan(organization)

        if domain.revoked_at is not None:
            raise AppError("DOMAIN_REVOKED", "Domain verification has been revoked.", status_code=403)

        assignment = await self.active_assignment(
            user_id=actor.id,
            organization_id=organization.id,
            hostname=hostname,
            profile_name=profile_name,
        )
        if assignment is not None:
            if (
                domain.is_verified
                and domain.verification_method == AUTHORIZATION_ADMIN_ASSIGNMENT
            ):
                return ScanAuthorization(
                    source=AUTHORIZATION_ADMIN_ASSIGNMENT,
                    hostname=hostname,
                    detail={"assignment_id": str(assignment.id)},
                )
            raise AppError(
                "DOMAIN_NOT_PROVISIONED",
                "Add the assigned test target to your project before scanning.",
                status_code=400,
            )

        if domain.verification_method == AUTHORIZATION_ADMIN_ASSIGNMENT and domain.is_verified:
            raise AppError(
                "ASSIGNMENT_REVOKED",
                "Test target assignment expired or was revoked.",
                status_code=403,
            )

        if (
            actor.dns_verification_exempt
            and actor.is_email_verified
            and await self.user_is_org_admin(actor.id, organization.id)
            and domain.verification_method == AUTHORIZATION_ADMIN_DNS_EXEMPT
            and domain.is_verified
            and verification_status(domain) == "verified"
        ):
            return ScanAuthorization(
                source=AUTHORIZATION_ADMIN_DNS_EXEMPT,
                hostname=hostname,
            )

        status = verification_status(domain)
        if status == "verified" and domain.verification_method in DNS_VERIFICATION_METHODS | {
            "manual_admin",
        }:
            active_profiles = {"deep", "code"}
            if profile_name in active_profiles and not domain.active_scan_allowed:
                raise AppError(
                    "ACTIVE_SCAN_NOT_ALLOWED",
                    "Active scanning requires domain admin approval.",
                    status_code=403,
                )
            return ScanAuthorization(source=AUTHORIZATION_DNS, hostname=hostname)

        if status == "expired":
            raise AppError(
                "DOMAIN_VERIFICATION_EXPIRED",
                "Domain verification has expired. Re-verify via DNS before scanning.",
                status_code=403,
            )
        raise AppError(
            "DOMAIN_NOT_VERIFIED",
            "Domain must be verified via DNS before scanning.",
            status_code=400,
        )

    async def assert_scan_authorized(
        self,
        *,
        actor: User,
        organization: Organization,
        domain: Domain,
        profile_name: str,
    ) -> ScanAuthorization:
        return await self.resolve_scan_authorization(
            actor=actor,
            organization=organization,
            domain=domain,
            profile_name=profile_name,
        )
