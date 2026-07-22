"""Continuous monitoring models."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MonitoringEventType(enum.StrEnum):
    NEW_FINDING = "new_finding"
    RESOLVED_FINDING = "resolved_finding"
    REDETECTED = "redetected"
    SEVERITY_CHANGED = "severity_changed"
    RISK_INCREASED = "risk_increased"
    RISK_DECREASED = "risk_decreased"


class ScanSchedule(Base, TimestampMixin):
    __tablename__ = "scan_schedules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    domain_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("domains.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scan_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="safe")
    interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_scan_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scan_jobs.id"))


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scan_schedules.id"), index=True)
    scan_job_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scan_jobs.id"), nullable=False)
    previous_scan_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scan_jobs.id"))
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("findings.id"))
    correlation_key: Mapped[str | None] = mapped_column(String(120))
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
