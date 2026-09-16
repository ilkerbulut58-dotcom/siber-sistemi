"""Predefined test scan targets and per-user assignments."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    pass


class PredefinedScanTarget(Base, TimestampMixin):
    __tablename__ = "predefined_scan_targets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_scan_profile: Mapped[str] = mapped_column(String(50), default="safe", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))

    assignments: Mapped[list["ScanTargetAssignment"]] = relationship(
        back_populates="target",
        cascade="all, delete-orphan",
    )


class ScanTargetAssignment(Base, TimestampMixin):
    __tablename__ = "scan_target_assignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    predefined_target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("predefined_scan_targets.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False, index=True
    )
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allowed_profiles: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))

    target: Mapped["PredefinedScanTarget"] = relationship(back_populates="assignments")
