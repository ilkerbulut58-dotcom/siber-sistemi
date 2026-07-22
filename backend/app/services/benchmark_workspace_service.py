"""Hidden system-scope workspace for isolated benchmark execution."""

from __future__ import annotations

from uuid import UUID

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Domain
from app.models.mixins import OrganizationRole
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project
from app.models.user import User

BENCHMARK_ORG_SLUG = "siber-benchmark-lab"
BENCHMARK_PROJECT_NAME = "Benchmark Lab"
BENCHMARK_USER_EMAIL = "benchmark-runner@system.internal"


class BenchmarkWorkspaceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_workspace(self) -> tuple[Organization, Project, User]:
        user = await self._ensure_runner_user()
        organization = await self._ensure_organization(user)
        project = await self._ensure_project(organization)
        return organization, project, user

    async def ensure_domain(self, organization: Organization, project: Project, hostname: str) -> Domain:
        result = await self.db.execute(
            select(Domain).where(
                Domain.organization_id == organization.id,
                Domain.project_id == project.id,
                Domain.hostname == hostname,
            )
        )
        domain = result.scalar_one_or_none()
        if domain is None:
            domain = Domain(
                organization_id=organization.id,
                project_id=project.id,
                hostname=hostname,
                is_verified=True,
            )
            self.db.add(domain)
            await self.db.flush()
        else:
            domain.is_verified = True
        return domain

    async def _ensure_runner_user(self) -> User:
        result = await self.db.execute(select(User).where(User.email == BENCHMARK_USER_EMAIL))
        user = result.scalar_one_or_none()
        if user is not None:
            return user
        from app.core.security import hash_password

        user = User(
            email=BENCHMARK_USER_EMAIL,
            password_hash=hash_password("benchmark-runner-not-for-login"),
            full_name="Benchmark Runner",
            is_active=True,
            is_platform_admin=False,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def _ensure_organization(self, owner: User) -> Organization:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == BENCHMARK_ORG_SLUG)
        )
        organization = result.scalar_one_or_none()
        if organization is None:
            organization = Organization(
                name="SIBER Benchmark Lab",
                slug=BENCHMARK_ORG_SLUG,
                owner_id=owner.id,
                is_system_scope=True,
            )
            self.db.add(organization)
            await self.db.flush()
            self.db.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=owner.id,
                    role=OrganizationRole.OWNER.value,
                    invited_by=owner.id,
                )
            )
        else:
            organization.is_system_scope = True
        return organization

    async def _ensure_project(self, organization: Organization) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.organization_id == organization.id,
                Project.name == BENCHMARK_PROJECT_NAME,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            project = Project(
                organization_id=organization.id,
                name=BENCHMARK_PROJECT_NAME,
                environment="staging",
            )
            self.db.add(project)
            await self.db.flush()
        return project
