"""Support access grant schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SupportGrantCreate(BaseModel):
    organization_id: UUID
    granted_to_user_id: UUID
    reason: str = Field(min_length=10, max_length=2000)
    duration_hours: int = Field(default=24, ge=1, le=168)


class SupportGrantResponse(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str | None = None
    granted_to_user_id: UUID
    granted_to_email: str | None = None
    granted_by_user_id: UUID
    reason: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
