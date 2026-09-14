"""Predefined scan targets and user assignments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PredefinedScanTargetResponse(BaseModel):
    id: UUID
    hostname: str
    display_name: str
    is_active: bool
    default_scan_profile: str
    notes: str | None = None

    model_config = {"from_attributes": True}


class ScanTargetAssignmentCreate(BaseModel):
    predefined_target_id: UUID
    user_id: UUID
    organization_id: UUID
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    allowed_profiles: list[str] = Field(default_factory=lambda: ["safe"])


class ScanTargetAssignmentResponse(BaseModel):
    id: UUID
    predefined_target_id: UUID
    user_id: UUID
    organization_id: UUID
    assigned_by_user_id: UUID
    starts_at: datetime
    ends_at: datetime | None
    allowed_profiles: list[str]
    revoked_at: datetime | None
    target: PredefinedScanTargetResponse | None = None

    model_config = {"from_attributes": True}
