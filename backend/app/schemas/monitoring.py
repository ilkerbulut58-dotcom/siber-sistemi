"""Monitoring API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ScanScheduleCreate(BaseModel):
    project_id: UUID
    domain_id: UUID
    name: str = Field(min_length=2, max_length=200)
    target_url: HttpUrl
    scan_profile: str = Field(default="safe")
    interval_hours: int = Field(default=24, ge=1, le=168)
    enabled: bool = True


class ScanScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    target_url: HttpUrl | None = None
    scan_profile: str | None = None
    interval_hours: int | None = Field(default=None, ge=1, le=168)
    enabled: bool | None = None


class ScanScheduleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    domain_id: UUID
    name: str
    target_url: str
    scan_profile: str
    interval_hours: int
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_scan_job_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MonitoringEventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    schedule_id: UUID | None
    scan_job_id: UUID
    previous_scan_job_id: UUID | None
    event_type: str
    finding_id: UUID | None
    correlation_key: str | None
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
