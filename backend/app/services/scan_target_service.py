"""Platform admin: predefined test targets and per-user assignments."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.models.organization import OrganizationMember
from app.models.scan_target import PredefinedScanTarget, ScanTargetAssignment
from app.models.user import User
from app.schemas.scan_target import ScanTargetAssignmentCreate
from app.services.audit_service import log_audit_event
from app.services.domain_verification_service import normalize_hostname


class ScanTargetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_targets(self) -> list[PredefinedScanTarget]:
        result = await self.db.execute(
            select(PredefinedScanTarget).order_by(PredefinedScanTarget.hostname)
        )
        return list(result.scalars())

    async def list_assignments(self, *, user_id: UUID | None = None) -> list[ScanTargetAssignment]:
        query = (
            select(ScanTargetAssignment)
            .options(selectinload(ScanTargetAssignment.target))
            .order_by(ScanTargetAssignment.created_at.desc())
        )
        if user_id is not None:
            query = query.where(ScanTargetAssignment.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars())

    async def create_assignment(
        self,
        data: ScanTargetAssignmentCreate,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> ScanTargetAssignment:
        target = await self.db.get(PredefinedScanTarget, data.predefined_target_id)
        if target is None or not target.is_active:
            raise AppError("NOT_FOUND", "Predefined scan target not found.", status_code=404)

        user = await self.db.get(User, data.user_id)
        if user is None or not user.is_active:
            raise AppError("NOT_FOUND", "User not found.", status_code=404)

        membership = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == data.user_id,
                OrganizationMember.organization_id == data.organization_id,
            )
        )
        if membership.scalar_one_or_none() is None:
            raise AppError(
                "INVALID_ASSIGNMENT",
                "User is not a member of the selected organization.",
                status_code=400,
            )

        starts_at = data.starts_at or datetime.now(UTC)
        assignment = ScanTargetAssignment(
            predefined_target_id=target.id,
            user_id=data.user_id,
            organization_id=data.organization_id,
            assigned_by_user_id=actor.id,
            starts_at=starts_at,
            ends_at=data.ends_at,
            allowed_profiles=data.allowed_profiles or [target.default_scan_profile],
        )
        self.db.add(assignment)
        await self.db.flush()
        await log_audit_event(
            self.db,
            action="scan_target.assigned",
            user_id=actor.id,
            organization_id=data.organization_id,
            resource_type="scan_target_assignment",
            resource_id=assignment.id,
            ip_address=ip_address,
            details={
                "hostname": normalize_hostname(target.hostname),
                "assigned_user_id": str(data.user_id),
                "allowed_profiles": assignment.allowed_profiles,
            },
        )
        await self.db.refresh(assignment)
        return assignment

    async def revoke_assignment(
        self,
        assignment_id: UUID,
        *,
        actor: User,
        ip_address: str | None = None,
    ) -> ScanTargetAssignment:
        assignment = await self.db.get(ScanTargetAssignment, assignment_id)
        if assignment is None:
            raise AppError("NOT_FOUND", "Assignment not found.", status_code=404)
        if assignment.revoked_at is not None:
            return assignment
        assignment.revoked_at = datetime.now(UTC)
        assignment.revoked_by_user_id = actor.id
        await log_audit_event(
            self.db,
            action="scan_target.assignment_revoked",
            user_id=actor.id,
            organization_id=assignment.organization_id,
            resource_type="scan_target_assignment",
            resource_id=assignment.id,
            ip_address=ip_address,
        )
        await self.db.flush()
        return assignment
