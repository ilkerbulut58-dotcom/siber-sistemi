"""Pilot tenant schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PilotTenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    is_pilot: bool
    pilot_starts_at: datetime | None
    pilot_ends_at: datetime | None
    pilot_scan_quota: int | None
    pilot_notes: str | None
    scans_disabled: bool
    pilot_active_scan_allowed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PilotTenantUpdate(BaseModel):
    is_pilot: bool | None = None
    pilot_starts_at: datetime | None = None
    pilot_ends_at: datetime | None = None
    pilot_scan_quota: int | None = Field(default=None, ge=1, le=1000)
    pilot_notes: str | None = Field(default=None, max_length=2000)
    scans_disabled: bool | None = None
    pilot_active_scan_allowed: bool | None = None
    is_active: bool | None = None


class OnboardingStepStatus(BaseModel):
    step_id: str
    label: str
    completed: bool


class OnboardingStatusResponse(BaseModel):
    organization_id: UUID
    is_pilot: bool
    steps: list[OnboardingStepStatus]
    ready_to_scan: bool
