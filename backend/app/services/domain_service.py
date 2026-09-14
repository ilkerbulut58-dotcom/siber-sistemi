"""Domain management business logic."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.domain import Domain, DomainVerification
from app.models.organization import Organization
from app.models.user import User
from app.schemas.domain import DomainCreate, VerificationInstructions, VerificationMethod
from app.services.audit_service import log_audit_event
from app.services.domain_authorization_service import (
    verification_expires_at,
)
from app.services.domain_verification_service import (
    build_instruction_fields,
    build_instructions,
    hostname_resolves,
    new_verification_token,
    normalize_hostname,
    run_verification_detailed,
)
from app.services.pilot_service import PilotService
from app.services.project_service import ProjectService
from app.services.scan_authorization_service import (
    AUTHORIZATION_ADMIN_ASSIGNMENT,
    AUTHORIZATION_ADMIN_DNS_EXEMPT,
    ScanAuthorizationService,
)


class DomainService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def _get_organization(self, organization_id: UUID) -> Organization:
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = result.scalar_one_or_none()
        if organization is None:
            raise AppError("NOT_FOUND", "Organization not found.", status_code=404)
        return organization

    def _auto_verify_enabled(self, organization: Organization) -> bool:
        return PilotService.relaxes_domain_verification(organization)

    def _mark_domain_verified(
        self,
        domain: Domain,
        *,
        method: str,
        verification: DomainVerification | None = None,
        allow_active_scan: bool = False,
    ) -> None:
        now = datetime.now(UTC)
        domain.is_verified = True
        domain.verified_at = now
        domain.last_checked_at = now
        domain.verification_method = method
        domain.revoked_at = None
        domain.revoked_by = None
        domain.verification_failure_reason = None
        domain.verification_expires_at = verification_expires_at(domain)
        domain.active_scan_allowed = allow_active_scan
        if verification is not None:
            verification.verified_at = now

    async def add(
        self,
        organization_id: UUID,
        project_id: UUID,
        data: DomainCreate,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> tuple[Domain, DomainVerification]:
        organization = await self._get_organization(organization_id)
        await ProjectService(self.db).get(organization_id, project_id)
        hostname = normalize_hostname(data.hostname)
        auto_verify = self._auto_verify_enabled(organization)

        if not auto_verify and not hostname_resolves(hostname):
            raise AppError(
                "INVALID_HOSTNAME",
                "Hostname could not be resolved. Check the domain name.",
                status_code=400,
            )

        existing = await self.db.execute(
            select(Domain).where(Domain.project_id == project_id, Domain.hostname == hostname)
        )
        if existing.scalar_one_or_none():
            raise AppError("DOMAIN_EXISTS", "Domain already added to this project.", status_code=409)

        domain = Domain(
            project_id=project_id,
            organization_id=organization_id,
            hostname=hostname,
        )

        self.db.add(domain)
        await self.db.flush()

        token, expires_at = new_verification_token()
        verification = DomainVerification(
            domain_id=domain.id,
            token=token,
            method=data.method.value,
            expires_at=expires_at,
        )
        auth_service = ScanAuthorizationService(self.db)
        assignment = await auth_service.active_assignment(
            user_id=actor.id,
            organization_id=organization_id,
            hostname=hostname,
            profile_name=None,
        )
        if assignment is not None:
            self._mark_domain_verified(
                domain,
                method=AUTHORIZATION_ADMIN_ASSIGNMENT,
                verification=verification,
                allow_active_scan=False,
            )
        elif auto_verify:
            self._mark_domain_verified(
                domain,
                method="test_skip",
                verification=verification,
                allow_active_scan=True,
            )
        self.db.add(verification)
        await self.db.flush()
        await self.db.refresh(domain)

        await log_audit_event(
            self.db,
            action="domain.added",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="domain",
            resource_id=domain.id,
            ip_address=ip_address,
            details={
                "hostname": hostname,
                "method": data.method.value,
                "auto_verified": auto_verify,
            },
        )
        return domain, verification

    async def list_for_project(self, organization_id: UUID, project_id: UUID) -> list[Domain]:
        await ProjectService(self.db).get(organization_id, project_id)
        result = await self.db.execute(
            select(Domain)
            .where(Domain.project_id == project_id, Domain.organization_id == organization_id)
            .order_by(Domain.hostname)
        )
        return list(result.scalars())

    async def get(self, organization_id: UUID, project_id: UUID, domain_id: UUID) -> Domain:
        result = await self.db.execute(
            select(Domain).where(
                Domain.id == domain_id,
                Domain.project_id == project_id,
                Domain.organization_id == organization_id,
            )
        )
        domain = result.scalar_one_or_none()
        if domain is None:
            raise AppError("NOT_FOUND", "Domain not found.", status_code=404)
        return domain

    async def delete(
        self,
        domain: Domain,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> None:
        await self.db.execute(delete(Domain).where(Domain.id == domain.id))
        await log_audit_event(
            self.db,
            action="domain.removed",
            user_id=actor.id,
            organization_id=domain.organization_id,
            resource_type="domain",
            resource_id=domain.id,
            ip_address=ip_address,
        )

    async def get_instructions(
        self,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
    ) -> VerificationInstructions:
        organization = await self._get_organization(organization_id)
        domain = await self.get(organization_id, project_id, domain_id)
        if self._auto_verify_enabled(organization):
            return VerificationInstructions(
                domain_id=domain.id,
                hostname=domain.hostname,
                method=VerificationMethod.DNS_TXT,
                token="test-mode",
                expires_at=datetime.now(UTC),
                instructions=["Development mode: DNS verification disabled."],
            )

        if domain.verification_method == AUTHORIZATION_ADMIN_ASSIGNMENT and domain.is_verified:
            return VerificationInstructions(
                domain_id=domain.id,
                hostname=domain.hostname,
                method=VerificationMethod.DNS_TXT,
                token="assigned",
                expires_at=domain.verification_expires_at or datetime.now(UTC),
                instructions=[
                    "Admin tarafından test için yetkilendirildi — DNS kaydı gerekmez.",
                ],
            )

        verification = await self._active_verification(domain.id)
        if verification is None:
            token, expires_at = new_verification_token()
            verification = DomainVerification(
                domain_id=domain.id,
                token=token,
                method=VerificationMethod.DNS_TXT.value,
                expires_at=expires_at,
            )
            self.db.add(verification)
            await self.db.flush()

        method = VerificationMethod(verification.method)
        fields = build_instruction_fields(method, domain.hostname, verification.token)
        return VerificationInstructions(
            domain_id=domain.id,
            hostname=domain.hostname,
            method=method,
            token=verification.token,
            expires_at=verification.expires_at,
            instructions=build_instructions(method, domain.hostname, verification.token),
            dns_host=fields.get("dns_host"),
            dns_value=fields.get("dns_value"),
            ttl_recommendation_seconds=fields.get("ttl_recommendation_seconds"),
            well_known_url=fields.get("well_known_url"),
            well_known_content=fields.get("well_known_content"),
            meta_tag_html=fields.get("meta_tag_html"),
            verification_valid_days=self.settings.domain_verification_ttl_days,
        )

    async def verify(
        self,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> tuple[Domain, bool, str, str | None]:
        organization = await self._get_organization(organization_id)
        domain = await self.get(organization_id, project_id, domain_id)

        if domain.revoked_at is not None:
            return domain, False, "Domain verification was revoked.", "DOMAIN_REVOKED"

        if self._auto_verify_enabled(organization):
            verification = await self._active_verification(domain.id)
            self._mark_domain_verified(
                domain,
                method="test_skip",
                verification=verification,
                allow_active_scan=True,
            )
            await log_audit_event(
                self.db,
                action="domain.verified",
                user_id=actor.id,
                organization_id=organization_id,
                resource_type="domain",
                resource_id=domain.id,
                ip_address=ip_address,
                details={"hostname": domain.hostname, "auto_verified": True, "method": "test_skip"},
            )
            await self.db.flush()
            await self.db.refresh(domain)
            return domain, True, "Development mode: domain auto-verified.", None

        verification = await self._active_verification(domain.id)
        if verification is None:
            token, expires_at = new_verification_token()
            verification = DomainVerification(
                domain_id=domain.id,
                token=token,
                method=VerificationMethod.DNS_TXT.value,
                expires_at=expires_at,
            )
            self.db.add(verification)
            await self.db.flush()

        if verification.expires_at is not None:
            expires_at = verification.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < datetime.now(UTC):
                return domain, False, "Verification token expired.", "VERIFICATION_EXPIRED"

        auth_service = ScanAuthorizationService(self.db)
        if (
            actor.dns_verification_exempt
            and actor.is_email_verified
            and await auth_service.user_is_org_admin(actor.id, organization_id)
        ):
            self._mark_domain_verified(
                domain,
                method=AUTHORIZATION_ADMIN_DNS_EXEMPT,
                verification=verification,
                allow_active_scan=False,
            )
            await log_audit_event(
                self.db,
                action="domain.verified",
                user_id=actor.id,
                organization_id=organization_id,
                resource_type="domain",
                resource_id=domain.id,
                ip_address=ip_address,
                details={"hostname": domain.hostname, "authorization": AUTHORIZATION_ADMIN_DNS_EXEMPT},
            )
            await self.db.flush()
            await self.db.refresh(domain)
            return domain, True, "Admin DNS exemption applied.", None

        verification.attempt_count += 1
        verification.last_attempt_at = datetime.now(UTC)
        method = VerificationMethod(verification.method)
        ok, failure_code = await run_verification_detailed(
            method, domain.hostname, verification.token
        )

        if ok:
            domain.is_verified = True
            domain.verified_at = datetime.now(UTC)
            domain.last_checked_at = datetime.now(UTC)
            domain.verification_method = method.value
            domain.revoked_at = None
            domain.revoked_by = None
            domain.verification_failure_reason = None
            domain.verification_expires_at = verification_expires_at(domain)
            verification.verified_at = datetime.now(UTC)
            message = "Domain verified successfully."
            failure_code = None
            await log_audit_event(
                self.db,
                action="domain.verified",
                user_id=actor.id,
                organization_id=organization_id,
                resource_type="domain",
                resource_id=domain.id,
                ip_address=ip_address,
            )
        else:
            domain.last_checked_at = datetime.now(UTC)
            message = "Verification failed."
            failure_code = failure_code or "VERIFICATION_FAILED"

        await self.db.flush()
        await self.db.refresh(domain)
        return domain, ok, message, failure_code

    async def revoke_verification(
        self,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
        *,
        actor: User,
        reason: str = "manual_revoke",
        ip_address: str | None = None,
    ) -> Domain:
        domain = await self.get(organization_id, project_id, domain_id)
        domain.is_verified = False
        domain.revoked_at = datetime.now(UTC)
        domain.revoked_by = actor.id
        domain.verification_failure_reason = reason
        domain.active_scan_allowed = False
        domain.verification_expires_at = None
        await log_audit_event(
            self.db,
            action="domain.verification_revoked",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="domain",
            resource_id=domain.id,
            ip_address=ip_address,
            details={"hostname": domain.hostname, "reason": reason},
        )
        await self.db.flush()
        await self.db.refresh(domain)
        return domain

    async def admin_approve_active_scan(
        self,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> Domain:
        domain = await self.get(organization_id, project_id, domain_id)
        if not domain.is_verified:
            raise AppError("DOMAIN_NOT_VERIFIED", "Domain must be verified before active scan approval.", status_code=400)
        domain.active_scan_allowed = True
        domain.admin_approved_at = datetime.now(UTC)
        domain.admin_approved_by = actor.id
        await log_audit_event(
            self.db,
            action="domain.active_scan_approved",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="domain",
            resource_id=domain.id,
            ip_address=ip_address,
            details={"hostname": domain.hostname, "verification_method": domain.verification_method},
        )
        await self.db.flush()
        await self.db.refresh(domain)
        return domain

    async def revoke_active_scan(
        self,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> Domain:
        domain = await self.get(organization_id, project_id, domain_id)
        domain.active_scan_allowed = False
        await log_audit_event(
            self.db,
            action="domain.active_scan_revoked",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="domain",
            resource_id=domain.id,
            ip_address=ip_address,
            details={"hostname": domain.hostname},
        )
        await self.db.flush()
        await self.db.refresh(domain)
        return domain

    async def platform_admin_verify_domain(
        self,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
        *,
        actor: User,
        approve_active_scan: bool = True,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Domain:
        domain = await self.get(organization_id, project_id, domain_id)
        domain.is_verified = True
        domain.verified_at = datetime.now(UTC)
        domain.last_checked_at = datetime.now(UTC)
        domain.verification_method = "manual_admin"
        domain.revoked_at = None
        domain.revoked_by = None
        domain.verification_failure_reason = None
        domain.verification_expires_at = verification_expires_at(domain)
        domain.admin_approved_by = actor.id
        if approve_active_scan:
            domain.active_scan_allowed = True
            domain.admin_approved_at = datetime.now(UTC)
        await log_audit_event(
            self.db,
            action="domain.verified",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="domain",
            resource_id=domain.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "hostname": domain.hostname,
                "verification_method": "manual_admin",
                "approved_by_platform_admin": True,
            },
        )
        if approve_active_scan:
            await log_audit_event(
                self.db,
                action="domain.active_scan_approved",
                user_id=actor.id,
                organization_id=organization_id,
                resource_type="domain",
                resource_id=domain.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"hostname": domain.hostname, "verification_method": "manual_admin"},
            )
        await self.db.flush()
        await self.db.refresh(domain)
        return domain

    async def _active_verification(self, domain_id: UUID) -> DomainVerification | None:
        result = await self.db.execute(
            select(DomainVerification)
            .where(
                DomainVerification.domain_id == domain_id,
                DomainVerification.verified_at.is_(None),
                DomainVerification.expires_at > datetime.now(UTC),
            )
            .order_by(DomainVerification.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
