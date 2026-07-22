"""Mobile application security models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MobilePlatform(enum.StrEnum):
    ANDROID = "android"
    IOS = "ios"


class MobileUploadStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    REJECTED = "rejected"


class MobileAnalysisStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MobileApplication(Base, TimestampMixin):
    __tablename__ = "mobile_applications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default=MobilePlatform.ANDROID)
    application_name: Mapped[str | None] = mapped_column(String(255))
    package_name: Mapped[str | None] = mapped_column(String(255))
    version_name: Mapped[str | None] = mapped_column(String(100))
    version_code: Mapped[str | None] = mapped_column(String(50))
    environment: Mapped[str] = mapped_column(String(30), nullable=False, default="staging")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    upload_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=MobileUploadStatus.UPLOADED
    )
    analysis_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=MobileAnalysisStatus.QUEUED
    )
    security_score: Mapped[float | None] = mapped_column(Float)
    findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql")
    )
    error_log: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
