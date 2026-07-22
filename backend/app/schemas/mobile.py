"""Mobile application security schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MobileApplicationUploadResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    platform: str
    application_name: str | None
    package_name: str | None
    version_name: str | None
    version_code: str | None
    environment: str
    original_filename: str
    file_size: int
    sha256: str
    upload_status: str
    analysis_status: str
    security_score: float | None
    findings_count: int
    analysis_summary: dict | None
    duplicate: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MobileApplicationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    platform: str
    application_name: str | None
    package_name: str | None
    version_name: str | None
    version_code: str | None
    environment: str
    original_filename: str
    file_size: int
    sha256: str
    upload_status: str
    analysis_status: str
    security_score: float | None
    findings_count: int
    analysis_summary: dict | None
    error_log: str | None
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MobileReportSummary(BaseModel):
    application_id: UUID
    package_name: str | None
    platform: str
    analysis_status: str
    security_score: float | None
    findings_count: int
    severity_counts: dict[str, int]
    masvs_categories: dict[str, int]
    analyzed_at: datetime | None
    generated_at: datetime


class MobileUploadForm(BaseModel):
    project_id: UUID
    environment: str = Field(default="staging", max_length=30)
