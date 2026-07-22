"""Target site intelligence snapshot collected during web scans."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TargetSiteProfile(Base):
    __tablename__ = "target_site_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False)
    scan_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("scan_jobs.id"), nullable=False, unique=True, index=True
    )
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
