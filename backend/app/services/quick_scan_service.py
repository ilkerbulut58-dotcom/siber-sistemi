"""One-step scan: workspace + domain + scan in a single call."""

from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Domain
from app.models.organization import Organization
from app.models.user import User
from app.schemas.domain import DomainCreate, VerificationMethod
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.quick_scan import QuickScanCreate, QuickScanResponse
from app.schemas.scan import ScanCreate, ScanResponse
from app.services.domain_service import DomainService
from app.services.domain_verification_service import normalize_hostname
from app.services.organization_service import OrganizationService
from app.services.project_service import ProjectService
from app.services.scan_service import ScanService


class QuickScanService:
    WORKSPACE_NAME = "Çalışma Alanım"
    PROJECT_NAME = "Web Sitelerim"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(
        self,
        data: QuickScanCreate,
        *,
        actor: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> QuickScanResponse:
        org = await self._ensure_organization(actor, ip_address=ip_address, user_agent=user_agent)
        project = await self._ensure_project(
            org.id,
            actor,
            scan_profile=data.scan_profile,
            ip_address=ip_address,
        )

        hostname = normalize_hostname(urlparse(str(data.target_url)).netloc or str(data.target_url))
        domain = await self._ensure_domain(
            org.id,
            project.id,
            hostname,
            actor,
            ip_address=ip_address,
        )

        scan = await ScanService(self.db).create(
            org.id,
            ScanCreate(
                project_id=project.id,
                domain_id=domain.id,
                scan_profile=data.scan_profile,
                target_url=data.target_url,
                authorization_accepted=data.authorization_accepted,
            ),
            actor=actor,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return QuickScanResponse(
            organization_id=org.id,
            project_id=project.id,
            domain_id=domain.id,
            scan=ScanResponse.model_validate(scan),
        )

    async def _ensure_organization(
        self,
        actor: User,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ):
        org_service = OrganizationService(self.db)
        result = await self.db.execute(
            select(Organization)
            .where(
                Organization.owner_id == actor.id,
                Organization.is_active.is_(True),
            )
            .order_by(Organization.created_at)
        )
        org = result.scalars().first()
        if org is not None:
            return org
        return await org_service.create(
            actor,
            OrganizationCreate(name=self.WORKSPACE_NAME),
            ip_address=ip_address,
            user_agent=user_agent,
        )

    STAGING_PROJECT_NAME = "Gelişmiş Taramalar"

    async def _ensure_project(
        self,
        organization_id: UUID,
        actor: User,
        *,
        scan_profile: str = "safe",
        ip_address: str | None,
    ):
        project_service = ProjectService(self.db)
        projects = await project_service.list_for_org(organization_id)

        if scan_profile in ("deep", "code"):
            for project in projects:
                if project.environment == "staging":
                    return project
            return await project_service.create(
                organization_id,
                ProjectCreate(name=self.STAGING_PROJECT_NAME, environment="staging"),
                actor=actor,
                ip_address=ip_address,
            )

        if projects:
            return projects[0]
        return await project_service.create(
            organization_id,
            ProjectCreate(name=self.PROJECT_NAME, environment="staging"),
            actor=actor,
            ip_address=ip_address,
        )

    async def _ensure_domain(
        self,
        organization_id: UUID,
        project_id: UUID,
        hostname: str,
        actor: User,
        *,
        ip_address: str | None,
    ) -> Domain:
        result = await self.db.execute(
            select(Domain).where(
                Domain.project_id == project_id,
                Domain.organization_id == organization_id,
                Domain.hostname == hostname,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        domain, _ = await DomainService(self.db).add(
            organization_id,
            project_id,
            DomainCreate(hostname=hostname, method=VerificationMethod.DNS_TXT),
            actor=actor,
            ip_address=ip_address,
        )
        return domain
