"""Organization and membership business logic."""

from uuid import UUID

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.models.mixins import OrganizationRole
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.schemas.organization import (
    MemberInviteRequest,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationUpdate,
)
from app.services.audit_service import log_audit_event


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        owner: User,
        data: OrganizationCreate,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Organization:
        slug = await self._unique_slug(data.name)
        organization = Organization(name=data.name, slug=slug, owner_id=owner.id)
        self.db.add(organization)
        await self.db.flush()

        membership = OrganizationMember(
            organization_id=organization.id,
            user_id=owner.id,
            role=OrganizationRole.OWNER.value,
            invited_by=owner.id,
        )
        self.db.add(membership)

        await log_audit_event(
            self.db,
            action="organization.created",
            user_id=owner.id,
            organization_id=organization.id,
            resource_type="organization",
            resource_id=organization.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"name": organization.name, "slug": organization.slug},
        )
        return organization

    async def create_managed_workspace(
        self,
        platform_admin: User,
        data: OrganizationCreate,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Organization:
        """Create an operator-owned workspace without exposing tenant data."""
        organization = await self.create(
            platform_admin,
            data,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        organization.is_managed_workspace = True
        await log_audit_event(
            self.db,
            action="platform.managed_workspace_created",
            user_id=platform_admin.id,
            organization_id=organization.id,
            resource_type="organization",
            resource_id=organization.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"name": organization.name},
        )
        return organization

    async def list_managed_workspaces(self) -> list[Organization]:
        result = await self.db.execute(
            select(Organization)
            .where(
                Organization.is_active.is_(True),
                Organization.is_managed_workspace.is_(True),
            )
            .order_by(Organization.name)
        )
        return list(result.scalars())

    async def list_for_user(self, user: User) -> list[Organization]:
        result = await self.db.execute(
            select(Organization)
            .join(OrganizationMember)
            .where(
                OrganizationMember.user_id == user.id,
                Organization.is_active.is_(True),
                Organization.is_system_scope.is_(False),
            )
            .order_by(Organization.name)
        )
        organizations = list(result.scalars().unique())

        if user.is_platform_admin:
            from app.services.support_grant_service import SupportGrantService

            grant_org_ids = await SupportGrantService(self.db).list_accessible_organization_ids(user)
            if grant_org_ids:
                existing_ids = {org.id for org in organizations}
                grant_result = await self.db.execute(
                    select(Organization).where(
                        Organization.id.in_(grant_org_ids),
                        Organization.is_active.is_(True),
                        Organization.is_system_scope.is_(False),
                    )
                )
                for org in grant_result.scalars():
                    if org.id not in existing_ids:
                        organizations.append(org)
                organizations.sort(key=lambda org: org.name.lower())

        return organizations

    async def update(
        self,
        organization: Organization,
        data: OrganizationUpdate,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> Organization:
        if data.name is not None:
            organization.name = data.name
        await self.db.flush()
        await self.db.refresh(organization)

        await log_audit_event(
            self.db,
            action="organization.updated",
            user_id=actor.id,
            organization_id=organization.id,
            resource_type="organization",
            resource_id=organization.id,
            ip_address=ip_address,
            details={"name": organization.name},
        )
        return organization

    async def delete(
        self,
        organization: Organization,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> None:
        if organization.is_managed_workspace:
            raise AppError(
                "PROTECTED_WORKSPACE",
                "Managed security workspaces cannot be deleted from the application.",
                status_code=403,
            )
        organization.is_active = False
        await log_audit_event(
            self.db,
            action="organization.deleted",
            user_id=actor.id,
            organization_id=organization.id,
            resource_type="organization",
            resource_id=organization.id,
            ip_address=ip_address,
        )

    async def list_members(self, org_id: UUID) -> list[OrganizationMemberResponse]:
        result = await self.db.execute(
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(OrganizationMember.organization_id == org_id)
            .order_by(OrganizationMember.joined_at)
        )
        members = result.scalars().all()
        return [
            OrganizationMemberResponse(
                id=member.id,
                organization_id=member.organization_id,
                user_id=member.user_id,
                role=OrganizationRole(member.role),
                invited_by=member.invited_by,
                joined_at=member.joined_at,
                email=member.user.email,
                full_name=member.user.full_name,
            )
            for member in members
        ]

    async def invite_member(
        self,
        organization: Organization,
        data: MemberInviteRequest,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> OrganizationMemberResponse:
        if data.role == OrganizationRole.OWNER:
            raise AppError("INVALID_ROLE", "Cannot assign owner role via invite.", status_code=400)

        user_result = await self.db.execute(
            select(User).where(User.email == data.email.lower(), User.is_active.is_(True))
        )
        invited_user = user_result.scalar_one_or_none()
        if invited_user is None:
            raise AppError(
                "USER_NOT_FOUND",
                "No active user found with that email.",
                status_code=404,
            )

        existing = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == invited_user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppError("MEMBER_EXISTS", "User is already a member.", status_code=409)

        member = OrganizationMember(
            organization_id=organization.id,
            user_id=invited_user.id,
            role=data.role.value,
            invited_by=actor.id,
        )
        self.db.add(member)
        await self.db.flush()

        await log_audit_event(
            self.db,
            action="organization.member_invited",
            user_id=actor.id,
            organization_id=organization.id,
            resource_type="organization_member",
            resource_id=member.id,
            ip_address=ip_address,
            details={"email": invited_user.email, "role": data.role.value},
        )

        return OrganizationMemberResponse(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=data.role,
            invited_by=member.invited_by,
            joined_at=member.joined_at,
            email=invited_user.email,
            full_name=invited_user.full_name,
        )

    async def update_member_role(
        self,
        organization: Organization,
        member_id: UUID,
        data: MemberRoleUpdate,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> OrganizationMemberResponse:
        if data.role == OrganizationRole.OWNER:
            raise AppError(
                "INVALID_ROLE",
                "Use ownership transfer to change owner.",
                status_code=400,
            )

        result = await self.db.execute(
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(
                OrganizationMember.id == member_id,
                OrganizationMember.organization_id == organization.id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise AppError("NOT_FOUND", "Member not found.", status_code=404)
        if member.role == OrganizationRole.OWNER.value:
            raise AppError("FORBIDDEN", "Cannot change the owner's role.", status_code=403)

        member.role = data.role.value
        await self.db.flush()

        await log_audit_event(
            self.db,
            action="organization.member_role_updated",
            user_id=actor.id,
            organization_id=organization.id,
            resource_type="organization_member",
            resource_id=member.id,
            ip_address=ip_address,
            details={"role": data.role.value},
        )

        return OrganizationMemberResponse(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=data.role,
            invited_by=member.invited_by,
            joined_at=member.joined_at,
            email=member.user.email,
            full_name=member.user.full_name,
        )

    async def remove_member(
        self,
        organization: Organization,
        member_id: UUID,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> None:
        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.id == member_id,
                OrganizationMember.organization_id == organization.id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise AppError("NOT_FOUND", "Member not found.", status_code=404)
        if member.role == OrganizationRole.OWNER.value:
            raise AppError("FORBIDDEN", "Cannot remove the organization owner.", status_code=403)

        await self.db.delete(member)
        await log_audit_event(
            self.db,
            action="organization.member_removed",
            user_id=actor.id,
            organization_id=organization.id,
            resource_type="organization_member",
            resource_id=member_id,
            ip_address=ip_address,
        )

    async def list_pilot_tenants(self) -> list[Organization]:
        result = await self.db.execute(
            select(Organization)
            .where(Organization.is_pilot.is_(True))
            .order_by(Organization.name)
        )
        return list(result.scalars())

    async def update_pilot_tenant(
        self,
        organization: Organization,
        data: "PilotTenantUpdate",
        *,
        actor: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Organization:
        from app.schemas.pilot import PilotTenantUpdate

        if not isinstance(data, PilotTenantUpdate):
            raise TypeError("Expected PilotTenantUpdate")

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(organization, field, value)
        await self.db.flush()
        await log_audit_event(
            self.db,
            action="pilot.tenant_updated",
            user_id=actor.id,
            organization_id=organization.id,
            resource_type="organization",
            resource_id=organization.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=updates,
        )
        return organization

    async def _unique_slug(self, name: str) -> str:
        base = slugify(name) or "organization"
        slug = base
        suffix = 1
        while True:
            result = await self.db.execute(select(Organization.id).where(Organization.slug == slug))
            if result.scalar_one_or_none() is None:
                return slug
            suffix += 1
            slug = f"{base}-{suffix}"
