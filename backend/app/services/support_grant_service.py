"""Platform support access grant business logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.organization import Organization
from app.models.support_grant import OrganizationSupportGrant
from app.models.user import User
from app.schemas.support_grant import SupportGrantCreate, SupportGrantResponse
from app.services.audit_service import log_audit_event


class SupportGrantService:
    MAX_DURATION_HOURS = 168

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def is_active(grant: OrganizationSupportGrant, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return grant.revoked_at is None and grant.expires_at > current

    async def get_active_grant(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationSupportGrant | None:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(OrganizationSupportGrant).where(
                OrganizationSupportGrant.organization_id == organization_id,
                OrganizationSupportGrant.granted_to_user_id == user_id,
                OrganizationSupportGrant.revoked_at.is_(None),
                OrganizationSupportGrant.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        actor: User,
        data: SupportGrantCreate,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SupportGrantResponse:
        if data.duration_hours > self.MAX_DURATION_HOURS:
            raise AppError(
                "INVALID_DURATION",
                f"Support access cannot exceed {self.MAX_DURATION_HOURS} hours.",
                status_code=400,
            )

        org_result = await self.db.execute(
            select(Organization).where(
                Organization.id == data.organization_id,
                Organization.is_active.is_(True),
            )
        )
        organization = org_result.scalar_one_or_none()
        if organization is None:
            raise AppError("NOT_FOUND", "Organization not found.", status_code=404)
        if organization.is_managed_workspace:
            raise AppError(
                "INVALID_TARGET",
                "Managed workspaces do not require support grants.",
                status_code=400,
            )
        if organization.is_system_scope:
            raise AppError(
                "INVALID_TARGET",
                "System-scope organizations cannot receive support grants.",
                status_code=400,
            )

        user_result = await self.db.execute(
            select(User).where(User.id == data.granted_to_user_id, User.is_active.is_(True))
        )
        granted_to = user_result.scalar_one_or_none()
        if granted_to is None:
            raise AppError("NOT_FOUND", "Target user not found.", status_code=404)
        if not granted_to.is_platform_admin:
            raise AppError(
                "INVALID_TARGET",
                "Support grants can only be issued to platform administrators.",
                status_code=400,
            )

        existing = await self.get_active_grant(
            organization_id=data.organization_id,
            user_id=data.granted_to_user_id,
        )
        if existing:
            raise AppError(
                "GRANT_EXISTS",
                "An active support grant already exists for this user and organization.",
                status_code=409,
            )

        expires_at = datetime.now(UTC) + timedelta(hours=data.duration_hours)
        grant = OrganizationSupportGrant(
            organization_id=data.organization_id,
            granted_to_user_id=data.granted_to_user_id,
            granted_by_user_id=actor.id,
            reason=data.reason.strip(),
            expires_at=expires_at,
        )
        self.db.add(grant)
        await self.db.flush()

        await log_audit_event(
            self.db,
            action="platform.support_grant_created",
            user_id=actor.id,
            organization_id=data.organization_id,
            resource_type="support_grant",
            resource_id=grant.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "granted_to_user_id": str(data.granted_to_user_id),
                "expires_at": expires_at.isoformat(),
                "duration_hours": data.duration_hours,
            },
        )

        return self._to_response(grant, organization=organization, granted_to=granted_to)

    async def revoke(
        self,
        *,
        grant_id: UUID,
        actor: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SupportGrantResponse:
        result = await self.db.execute(
            select(OrganizationSupportGrant).where(OrganizationSupportGrant.id == grant_id)
        )
        grant = result.scalar_one_or_none()
        if grant is None:
            raise AppError("NOT_FOUND", "Support grant not found.", status_code=404)
        if grant.revoked_at is not None:
            raise AppError("ALREADY_REVOKED", "Support grant is already revoked.", status_code=409)

        grant.revoked_at = datetime.now(UTC)
        grant.revoked_by_user_id = actor.id
        await self.db.flush()

        await log_audit_event(
            self.db,
            action="platform.support_grant_revoked",
            user_id=actor.id,
            organization_id=grant.organization_id,
            resource_type="support_grant",
            resource_id=grant.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        org_result = await self.db.execute(
            select(Organization).where(Organization.id == grant.organization_id)
        )
        organization = org_result.scalar_one_or_none()
        user_result = await self.db.execute(
            select(User).where(User.id == grant.granted_to_user_id)
        )
        granted_to = user_result.scalar_one_or_none()
        return self._to_response(grant, organization=organization, granted_to=granted_to)

    async def list_grants(
        self,
        *,
        active_only: bool = True,
        organization_id: UUID | None = None,
    ) -> list[SupportGrantResponse]:
        now = datetime.now(UTC)
        query = select(OrganizationSupportGrant).order_by(
            OrganizationSupportGrant.created_at.desc()
        )
        if organization_id:
            query = query.where(OrganizationSupportGrant.organization_id == organization_id)
        if active_only:
            query = query.where(
                OrganizationSupportGrant.revoked_at.is_(None),
                OrganizationSupportGrant.expires_at > now,
            )

        result = await self.db.execute(query.limit(100))
        grants = list(result.scalars())

        org_ids = {grant.organization_id for grant in grants}
        user_ids = {grant.granted_to_user_id for grant in grants}

        org_map: dict[UUID, Organization] = {}
        if org_ids:
            org_result = await self.db.execute(
                select(Organization).where(Organization.id.in_(org_ids))
            )
            org_map = {org.id: org for org in org_result.scalars()}

        user_map: dict[UUID, User] = {}
        if user_ids:
            user_result = await self.db.execute(select(User).where(User.id.in_(user_ids)))
            user_map = {user.id: user for user in user_result.scalars()}

        return [
            self._to_response(
                grant,
                organization=org_map.get(grant.organization_id),
                granted_to=user_map.get(grant.granted_to_user_id),
            )
            for grant in grants
        ]

    async def list_accessible_organization_ids(self, user: User) -> list[UUID]:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(OrganizationSupportGrant.organization_id).where(
                OrganizationSupportGrant.granted_to_user_id == user.id,
                OrganizationSupportGrant.revoked_at.is_(None),
                OrganizationSupportGrant.expires_at > now,
            )
        )
        return list(result.scalars().unique())

    def _to_response(
        self,
        grant: OrganizationSupportGrant,
        *,
        organization: Organization | None,
        granted_to: User | None,
    ) -> SupportGrantResponse:
        return SupportGrantResponse(
            id=grant.id,
            organization_id=grant.organization_id,
            organization_name=organization.name if organization else None,
            granted_to_user_id=grant.granted_to_user_id,
            granted_to_email=granted_to.email if granted_to else None,
            granted_by_user_id=grant.granted_by_user_id,
            reason=grant.reason,
            expires_at=grant.expires_at,
            revoked_at=grant.revoked_at,
            created_at=grant.created_at,
            is_active=self.is_active(grant),
        )
