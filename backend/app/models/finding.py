"""Security finding models."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class FindingSeverity(enum.StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(enum.StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"
    INCONCLUSIVE = "inconclusive"
    NEEDS_HELP = "needs_help"
    DUPLICATE = "duplicate"
    NOT_APPLICABLE = "not_applicable"


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    scan_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scan_jobs.id"), nullable=True, index=True
    )
    source_tool: Mapped[str] = mapped_column(String(50), nullable=False)
    source_rule_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    affected_url: Mapped[str | None] = mapped_column(String(1000))
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default=FindingSeverity.MEDIUM)
    confidence: Mapped[str | None] = mapped_column(String(20))
    correlation_key: Mapped[str | None] = mapped_column(String(120), index=True)
    risk_score: Mapped[float | None] = mapped_column(Float)
    cvss_score: Mapped[float | None] = mapped_column(Float)
    source_tools: Mapped[list | None] = mapped_column(JSON)
    verification_status: Mapped[str | None] = mapped_column(String(30))
    verification_notes: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("assets.id"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=FindingStatus.OPEN)
    remediation: Mapped[str | None] = mapped_column(Text)
    risk_explanation: Mapped[str | None] = mapped_column(Text)
    remediation_steps: Mapped[list | None] = mapped_column(JSON)
    config_file_paths: Mapped[list | None] = mapped_column(JSON)
    config_snippet: Mapped[str | None] = mapped_column(Text)
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_remediation: Mapped[str | None] = mapped_column(Text)
    ai_confidence_label: Mapped[str | None] = mapped_column(String(50))
    risk_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    risk_model_version: Mapped[str | None] = mapped_column(String(20))
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False, default="web")
    platform: Mapped[str | None] = mapped_column(String(20))
    masvs_category: Mapped[str | None] = mapped_column(String(80))
    affected_component: Mapped[str | None] = mapped_column(String(500))
    mobile_application_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
