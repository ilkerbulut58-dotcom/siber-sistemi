"""Scan schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ScanProfileResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ScanCreate(BaseModel):
    project_id: UUID
    domain_id: UUID
    scan_profile: str = Field(default="safe")
    target_url: HttpUrl
    authorization_accepted: bool = Field(description="User confirms authorization to scan")
    scope_config: dict | None = None


class ScanResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    domain_id: UUID
    initiated_by: UUID
    scan_profile: str
    target_url: str
    status: str
    findings_count: int
    error_log: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanStatusResponse(BaseModel):
    id: UUID
    status: str
    findings_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error_log: str | None

    model_config = {"from_attributes": True}
