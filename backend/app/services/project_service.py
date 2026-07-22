"""Project business logic."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.audit_service import log_audit_event


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        organization_id: UUID,
        data: ProjectCreate,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> Project:
        project = Project(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
            environment=data.environment,
        )
        self.db.add(project)
        await self.db.flush()
        await log_audit_event(
            self.db,
            action="project.created",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="project",
            resource_id=project.id,
            ip_address=ip_address,
            details={"name": project.name},
        )
        return project

    async def list_for_org(self, organization_id: UUID) -> list[Project]:
        result = await self.db.execute(
            select(Project)
            .where(Project.organization_id == organization_id, Project.is_active.is_(True))
            .order_by(Project.name)
        )
        return list(result.scalars())

    async def get(self, organization_id: UUID, project_id: UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
                Project.is_active.is_(True),
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise AppError("NOT_FOUND", "Project not found.", status_code=404)
        return project

    async def update(
        self,
        project: Project,
        data: ProjectUpdate,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> Project:
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.environment is not None:
            project.environment = data.environment
        await self.db.flush()
        await log_audit_event(
            self.db,
            action="project.updated",
            user_id=actor.id,
            organization_id=project.organization_id,
            resource_type="project",
            resource_id=project.id,
            ip_address=ip_address,
        )
        return project

    async def delete(
        self,
        project: Project,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> None:
        project.is_active = False
        await log_audit_event(
            self.db,
            action="project.deleted",
            user_id=actor.id,
            organization_id=project.organization_id,
            resource_type="project",
            resource_id=project.id,
            ip_address=ip_address,
        )
