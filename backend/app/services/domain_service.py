"""Domain management business logic."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.domain import Domain, DomainVerification
from app.models.user import User
from app.schemas.domain import DomainCreate, VerificationInstructions, VerificationMethod
from app.services.audit_service import log_audit_event
from app.services.domain_verification_service import (
    build_instructions,
    hostname_resolves,
    new_verification_token,
    normalize_hostname,
    run_verification,
)
from app.services.project_service import ProjectService


class DomainService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def add(
        self,
        organization_id: UUID,
        project_id: UUID,
        data: DomainCreate,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> tuple[Domain, DomainVerification]:
        await ProjectService(self.db).get(organization_id, project_id)
        hostname = normalize_hostname(data.hostname)

        if not self.settings.skip_domain_verification and not hostname_resolves(hostname):
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
        if self.settings.skip_domain_verification:
            domain.is_verified = True
            domain.verified_at = datetime.now(UTC)

        self.db.add(domain)
        await self.db.flush()

        token, expires_at = new_verification_token()
        verification = DomainVerification(
            domain_id=domain.id,
            token=token,
            method=data.method.value,
            expires_at=expires_at,
        )
        if self.settings.skip_domain_verification:
            verification.verified_at = datetime.now(UTC)
        self.db.add(verification)
        await self.db.flush()

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
                "auto_verified": self.settings.skip_domain_verification,
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
        if self.settings.skip_domain_verification:
            domain = await self.get(organization_id, project_id, domain_id)
            return VerificationInstructions(
                domain_id=domain.id,
                hostname=domain.hostname,
                method=VerificationMethod.DNS_TXT,
                token="test-mode",
                expires_at=datetime.now(UTC),
                instructions=["Test modu: DNS doğrulama devre dışı. Domain otomatik onaylı."],
            )

        domain = await self.get(organization_id, project_id, domain_id)
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
        return VerificationInstructions(
            domain_id=domain.id,
            hostname=domain.hostname,
            method=method,
            token=verification.token,
            expires_at=verification.expires_at,
            instructions=build_instructions(method, domain.hostname, verification.token),
        )

    async def verify(
        self,
        organization_id: UUID,
        project_id: UUID,
        domain_id: UUID,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> tuple[Domain, bool, str]:
        domain = await self.get(organization_id, project_id, domain_id)

        if self.settings.skip_domain_verification:
            domain.is_verified = True
            domain.verified_at = datetime.now(UTC)
            domain.last_checked_at = datetime.now(UTC)
            await self.db.flush()
            await self.db.refresh(domain)
            return domain, True, "Test modu: domain otomatik doğrulandı."

        verification = await self._active_verification(domain.id)
        if verification is None:
            raise AppError("NO_VERIFICATION", "No active verification token.", status_code=400)

        verification.attempt_count += 1
        verification.last_attempt_at = datetime.now(UTC)
        method = VerificationMethod(verification.method)
        ok = await run_verification(method, domain.hostname, verification.token)

        if ok:
            domain.is_verified = True
            domain.verified_at = datetime.now(UTC)
            domain.last_checked_at = datetime.now(UTC)
            domain.verification_method = method.value
            verification.verified_at = datetime.now(UTC)
            message = "Domain verified successfully."
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
            message = "Verification failed. Check instructions and try again."

        await self.db.flush()
        await self.db.refresh(domain)
        return domain, ok, message

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
